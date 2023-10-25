import csv
import logging

import cx_Oracle
from canvas_api.helpers import courses as canvas_api_helper_courses
from canvas_api.helpers import enrollments as canvas_api_helper_enrollments
from canvas_api.helpers import sections as canvas_api_helper_sections
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_common.models import CourseInstance

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000

class Command(BaseCommand):
    help = 'Imports data from CSV to generate CourseInstance records'

    def add_arguments(self, parser):
        parser.add_argument('csvfile', type=open)
        parser.add_argument('--load', action='store_true', help='Load data into a temporary table for later processing')
        parser.add_argument('--migrate_from_tmp_db', action='store_true', help='Migrate data from the temporary table to Coursemanager')
        parser.add_argument('--update_canvas_sections', action='store_true', help='Update Canvas sections')
        parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without inserting into the database')

    def handle(self, *args, **options):
        csvfile = options['csvfile']

        if options['load']:
            create_temp_table()
            with connection.cursor() as cursor:
                cursor.execute("SELECT MAX(row_index) FROM temp_courseinstance")
                start_index = cursor.fetchone()[0]
            reader = csv.DictReader(csvfile)
            while True:
                with connections['coursemanager'].cursor() as cursor:
                    cursor.execute("SELECT MAX(row_index) FROM temp_courseinstance")
                    start_index = cursor.fetchone()[0] or 0
                data = generate_data_for_temp_table(reader, start_index=start_index)
                if not data:
                    break
                if options['dry_run']:
                    self.stdout.write(self.style.SUCCESS('dry-run mode: data not loaded into temp_courseinstance'))
                    with open('dry_run_load.txt', 'a') as f:
                        for instance in data:
                            f.write(str(instance) + '\n')
                else:
                    insert_temp_data(data)
                    self.stdout.write(self.style.SUCCESS('Batch loaded into the temporary table'))
            self.stdout.write(self.style.SUCCESS('Data loading job complete'))

        elif options['migrate_from_tmp_db']:
            while True:
                instances = generate_instances_for_coursemanager()
                if not instances:
                    break
                if options['dry_run']:
                    with open('dry_run_migrate.txt', 'a') as f:
                        for instance in instances:
                            f.write(str(instance) + '\n')
                    self.stdout.write(self.style.SUCCESS('dry-run mode: data not migrated fropm temp_courseinstance to COURSE_INSTANCE'))
                else:
                    bulk_insert_course_instances(instances)
                    self.stdout.write(self.style.SUCCESS('Data migrated from temp_courseinstance to COURSE_INSTANCE'))

        elif options['update_canvas_sections']:
            while True:
                instances = get_instances_for_canvas()
                if not instances:
                    break
                if options['dry_run']:
                    with open('dry_run_update_canvas_sections.txt', 'a') as f:
                        for instance in instances:
                            f.write(str(instance) + '\n')
                    self.stdout.write(self.style.SUCCESS('dry-run mode: Canvas sections not updated with new COURSE_INSTANCE data'))
                else:
                    update_canvas_section(instances)
                    self.stdout.write(self.style.SUCCESS('Canvas sections updated with new COURSE_INSTANCE data'))

        else:
            self.stdout.write(self.style.ERROR('Please specify either --load, --migrate_from_tmp_db, or --update_canvas_sections'))


def get_instances_for_canvas():
    with connections['coursemanager'].cursor() as cursor:
        cursor.execute(f"""
            SELECT * FROM temp_courseinstance
            WHERE updated_in_canvas=0
            FETCH FIRST {BATCH_SIZE} ROWS ONLY
        """)
        return cursor.fetchall()


def update_canvas_section(instance_id_pairs):
    for instance, instance_id in instance_id_pairs:
        canvas_course_id = instance[canvas_course_id]
        section_id = instance[canvas_section_id]

        try:
            course_section = canvas_api_helper_sections.update_section(canvas_course_id, section_id, course_section_sis_section_id=instance_id)
            success = True
        except Exception as e:
            logger.exception(f'Unable to update section with section_id={section_id} to sis_section_id={instance_id} in Canvas')
            output_errors([f"canvas_course_id={canvas_course_id}, section_id={section_id}, sis_section_id={instance_id}: {e}"])
            success = False

        if success:
            canvas_api_helper_courses.delete_cache(canvas_course_id=canvas_course_id)
            canvas_api_helper_enrollments.delete_cache(canvas_course_id)
            # update tmp record with successful update
            update_updated_in_canvas_flag(instance_id, 1)

        else:
            output_errors([f"update_canvas_section error: canvas_course_id={canvas_course_id}"])


def generate_data_for_temp_table(reader, batch_size=BATCH_SIZE, start_index=0) -> list[dict]:
    skipped = []
    errors = []
    data = []
    for i, row in enumerate(reader, start=start_index):
        parent_sis_course_id = row['course_id_x']
        if parent_sis_course_id:
            logger.debug(f'Processing sis_course_id {parent_sis_course_id}')

            # check that the ID is a number
            try:
                int(parent_sis_course_id)
            except ValueError as e:
                logger.warning(f"sis_course_id {parent_sis_course_id} not a valid SIs ID")
                errors.append(f'{row}: {e}')
                continue

            # We now need to get the corresponding parent_course_instance
            try:
                parent_course_instance = CourseInstance.objects.get(course_instance_id=parent_sis_course_id)
            except Exception as e:
                logger.warning(f'Error retrieving parent_course_instance: {e}')
                errors.append(f'{row}: {e}')
                continue

            # Get section name, id from CSV
            name = row['name']
            canvas_section_id = row['canvas_section_id']
            canvas_course_id = row['canvas_course_id']

            data.append({
                'row_index': i,
                'cs_class_type': 'N',
                'parent_course_instance_id': parent_course_instance.course_instance_id,
                'course_id': parent_course_instance.course_id,
                'term': parent_course_instance.term,
                'source': 'managecrs',
                'sync_to_canvas': 1,
                'title': name.strip(),
                'short_title': name.strip(),
                'section_id': canvas_section_id,
                'canvas_course_id': canvas_course_id,
                'updated_in_db': 0,
                'updated_in_canvas': 0
            })
        else:
            logger.debug(f'No section_id for row index={i}, canvas_course_id={row["canvas_course_id"]} -- skipping')
            skipped.append(f'{row}')

        # If the data list has reached the batch size, return it
        if len(data) == batch_size:
            output_errors(errors)
            output_skipped(skipped)
            return data

    # We're out of the loop, meaning we've processed all the data.
    # If there's any data left, return it.
    output_skipped(skipped)
    output_errors(errors)
    return data


def output_errors(errors):
    if errors:
        with open('errors.txt', 'a') as f:
            for error in errors:
                f.write(str(error) + '\n')
    return


def output_skipped(skipped):
    if skipped:
        with open('skipped.txt', 'a') as f:
            for row in skipped:
                f.write(str(row) + '\n')
    return


def create_temp_table():
    with connections['coursemanager'].cursor() as cursor:
        try:
            cursor.execute("""
                CREATE TABLE temp_courseinstance
                (
                    id NUMBER GENERATED ALWAYS AS IDENTITY,
                    row_index NUMBER,
                    cs_class_type VARCHAR2(1),
                    parent_course_instance_id NUMBER,
                    course_id NUMBER,
                    term_id VARCHAR2(100),
                    source VARCHAR2(100),
                    sync_to_canvas NUMBER,
                    title VARCHAR2(255),
                    short_title VARCHAR2(255),
                    section_id NUMBER,
                    canvas_course_id NUMBER,
                    updated_in_db NUMBER,
                    updated_in_canvas NUMBER
                )
            """)
        except Exception as e:
            if 'ORA-00955: name is already used by an existing object' in str(e):
                pass
            else:
                raise e
        connections['coursemanager'].commit()


def insert_temp_data(data):
    try:
        with transaction.atomic():
            with connections['coursemanager'].cursor() as cursor:
                insert_query = """
                    INSERT INTO temp_courseinstance (
                        row_index,
                        cs_class_type,
                        parent_course_instance_id,
                        course_id,
                        term,
                        source,
                        sync_to_canvas,
                        title,
                        short_title,
                        section_id,
                        updated_in_db,
                        updated_in_canvas
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                # Convert data to list of tuples for executemany command
                data_tuples = [(d['row_index'], d['sis_course_id'], d['cs_class_type'], d['parent_course_instance_id'], d['course_id'], d['term'], d['source'], d['sync_to_canvas'], d['title'], d['short_title']) for d in data]
                cursor.executemany(insert_query, data_tuples, batcherrors=True)
                connection.commit()
    except Exception as e:
        logger.exception(f'Failed to insert data into the temporary table: {e}')
        # Write the problematic instances to a text file
        with open('insert_temp_data_errors.txt', 'a') as f:
            f.write(f"data={data_tuples}, error={e}" + '\n')
        return


def generate_instances_for_coursemanager():
    with connections['coursemanager'].cursor() as cursor:
        cursor.execute(f"""
            SELECT * FROM temp_courseinstance
            WHERE updated_in_db=0
            FETCH FIRST {BATCH_SIZE} ROWS ONLY
        """)
        rows = cursor.fetchall()

    instances = []
    for row in rows:
        instance = (
            row[1],  # cs_class_type
            row[2],  # parent_course_instance_id
            row[3],  # course_id
            row[4],  # term
            row[5],  # source
            row[6],  # sync_to_canvas
            row[7],  # title
            row[8],  # short_title
            row[9],  # section_id
            row[10],  # canvas_course_id
            row[11],  # updated_in_db
            row[12]   # updated_in_canvas
        )
        instances.append(instance)

    return instances


def bulk_insert_course_instances(instances):
    with connections['coursemanager'].cursor() as cursor:
        # Get the actual cx_Oracle.Cursor object
        cx_cursor = cursor.cursor

        placeholders = ', '.join(['(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'] * len(instances))

        try:
            cx_cursor.execute(
                f"""
                INSERT INTO COURSE_INSTANCE (cs_class_type, parent_course_instance_id, course_id, term, source, sync_to_canvas, title, short_title, section_id, canvas_course_id, updated_in_db, updated_in_canvas)
                VALUES {placeholders}
                RETURNING id INTO :ids
                """,
                instances
            )
            connections['coursemanager'].commit()
        except cx_Oracle.DatabaseError as e:
            error, = e.args
            logger.exception(f'Error inserting data into COURSE_INSTANCE table: {e}')
            output_errors([f'bulk_insert_course_instances error: error={error}, e={e}'])
            return

        # Get the IDs of the inserted rows
        ids = cx_cursor.var(cx_Oracle.NUMBERARRAY)
        cx_cursor.execute(None, ids=ids)
        ids = ids.values

        update_data = [(instance, id) for instance, id in zip(instances, ids)]

        update_sis_section_ids(update_data)
        update_canvas_section(update_data)

    return ids


def update_sis_section_ids(ids):
    with connections['coursemanager'].cursor() as cursor:
        placeholders = ', '.join(['(%s, %s)'] * len(ids))

        cursor.execute(
            f"""
            UPDATE temp_courseinstance
            SET sis_section_id = CASE id
                {placeholders}
            END
            """,
            ids
        )
        connections['coursemanager'].commit()


def update_updated_in_canvas_flag(instance_id, value):
    with connections['coursemanager'].cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE temp_courseinstance
            SET updated_in_canvas = {value}
            WHERE id = {instance_id}
            """
        )
        connections['coursemanager'].commit()


def update_updated_in_db_flag(ids):
    with connections['coursemanager'].cursor() as cursor:
        placeholders = ', '.join(['(%s)'] * len(ids))

        cursor.execute(
            f"""
            UPDATE temp_courseinstance
            SET updated_in_db = 1
            WHERE id IN {placeholders}
            """,
            ids
        )
        connections['coursemanager'].commit()
