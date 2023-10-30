import csv
import logging

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
        parser.add_argument('--enable_sync_to_canvas', action='store_true', help='Update sync_to_canvas attribute of CourseInstance records')
        parser.add_argument('--reverse', action='store_true', help='Reverses the Canvas and Coursemanager updates to their original states')
        parser.add_argument('--dry-run', action='store_true', help='Perform a dry run without inserting into the database')

    def handle(self, **options):
        csvfile = options['csvfile']

        if options['load']:
            create_temp_table()
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
                    ids = bulk_insert_course_instances(instances)
                    if not ids:
                        self.stdout.write(self.style.ERROR('Error during bulk creation'))
                        break
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

        elif options['enable_sync_to_canvas']:
            update_course_instance_sync_to_canvas()

        elif options['reverse']:
            reverse()

        else:
            self.stdout.write(self.style.ERROR('Please specify either --load, --migrate_from_tmp_db, --update_canvas_sections, --enable_sync_to_canvas, or --reverse'))


def get_instances_for_canvas(reverse=False):
    if reverse:
        with connections['coursemanager'].cursor() as cursor:
            # if reversing the operation, just grab all records where canvas has been updated
            cursor.execute("SELECT * FROM temp_courseinstance WHERE updated_in_canvas=1 AND course_instance_id IS NOT NULL")
            return cursor.fetchall()
    else:
        with connections['coursemanager'].cursor() as cursor:
            cursor.execute("SELECT * FROM temp_courseinstance WHERE updated_in_canvas=0 AND course_instance_id IS NOT NULL FETCH FIRST %s ROWS ONLY", [BATCH_SIZE])
            return cursor.fetchall()


def update_canvas_section(instances, reverse=False):
    successful_temp_ids = []
    for instance in instances:
        canvas_course_id = instance[11]
        section_id = instance[10]
        instance_id = instance[14]

        if reverse:
            instance_id = ''

        try:
            course_section = canvas_api_helper_sections.update_section(canvas_course_id, section_id, course_section_sis_section_id=instance_id)
        except Exception as e:
            logger.exception(f'Unable to update section with section_id={section_id} to sis_section_id={instance_id} in Canvas')
            output_errors([f"canvas_course_id={canvas_course_id}, section_id={section_id}, sis_section_id={instance_id}: {e}"])
            continue

        if not course_section:
            logger.warning(f'Section not updated. Instance={instance}')
            output_errors([f"canvas_course_id={canvas_course_id}, section_id={section_id}, sis_section_id={instance_id}"])
            continue

        logger.debug(f'Updated course_section={course_section}')
        canvas_api_helper_courses.delete_cache(canvas_course_id=canvas_course_id)
        canvas_api_helper_enrollments.delete_cache(canvas_course_id)

        successful_temp_ids.append((instance[0],))

    if reverse:
        update_updated_in_canvas_flag(successful_temp_ids, reverse=True)
    else:
        update_updated_in_canvas_flag(successful_temp_ids)


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
                'term_id': parent_course_instance.term.term_id,
                'source': 'managecrs',
                'sync_to_canvas': 0,
                'title': name.strip(),
                'short_title': name.strip(),
                'section_id': canvas_section_id,
                'canvas_course_id': canvas_course_id,
                'course_instance_id': None,
                'updated_in_db': 0,
                'updated_in_canvas': 0
            })
        else:
            logger.debug(f'No parent_sis_course_id for row index={i}, canvas_course_id={row["canvas_course_id"]} -- skipping')
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
                    term_id NUMBER,
                    source VARCHAR2(100),
                    sync_to_canvas NUMBER,
                    title VARCHAR2(255),
                    short_title VARCHAR2(255),
                    section_id NUMBER,
                    canvas_course_id NUMBER,
                    course_instance_id NUMBER,
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
                        term_id,
                        source,
                        sync_to_canvas,
                        title,
                        short_title,
                        section_id,
                        canvas_course_id,
                        course_instance_id,
                        updated_in_canvas
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                # Convert data to list of tuples for executemany command
                data_tuples = [(d['row_index'], d['cs_class_type'], d['parent_course_instance_id'], d['course_id'], d['term_id'], d['source'], d['sync_to_canvas'], d['title'], d['short_title'], d['section_id'], d['canvas_course_id'], d['course_instance_id'], d['updated_in_canvas']) for d in data]
                cursor.executemany(insert_query, data_tuples)
                connections['coursemanager'].commit()
    except Exception as e:
        logger.exception(f'Failed to insert data into the temporary table: {e}')
        # Write the problematic instances to a text file
        with open('insert_temp_data_errors.txt', 'a') as f:
            f.write(f"data={data_tuples}, error={e}" + '\n')
        return


def generate_instances_for_coursemanager():
    with connections['coursemanager'].cursor() as cursor:
        cursor.execute("SELECT * FROM temp_courseinstance WHERE course_instance_id IS NULL FETCH FIRST %s ROWS ONLY", [BATCH_SIZE])
        rows = cursor.fetchall()

    instances = []
    for row in rows:
        instance_dict = {
            'temp_id': row[0],
            'row_index': row[1],
            'cs_class_type': row[2],
            'parent_course_instance_id': row[3],
            'course_id': row[4],
            'term_id': int(row[5]),
            'source': row[6],
            'sync_to_canvas': row[7],
            'title': row[8],
            'short_title': row[9],
            'course_instance_id': row[14],
        }
        instances.append(instance_dict)

    return instances


def bulk_insert_course_instances(instances):
    created_instances = []

    for instance in instances:
        try:
            course_instance = CourseInstance(
                cs_class_type=instance['cs_class_type'],
                parent_course_instance_id=instance['parent_course_instance_id'],
                course_id=instance['course_id'],
                term_id=int(instance['term_id']),
                source=instance['source'],
                sync_to_canvas=instance['sync_to_canvas'],
                title=instance['title'],
                short_title=instance['short_title']
            )
            course_instance.save()
            logger.debug(f"successfully created ci_id={course_instance.course_instance_id}" )
        except Exception as e:
            logger.exception(f'Exception creating course_instance: {e}')
            with open('created_db_errors.txt', 'a') as f:
                f.write(f"error={e}" + '\n')
            continue

        created_instances.append(course_instance)

    logger.debug(f"successfully created {len(created_instances)} course_instances" )

    # Pair each created CourseInstance with its corresponding temp_id
    created_instances_with_ids = []
    for instance, original_instance in zip(created_instances, instances):
        created_instances_with_ids.append((instance.course_instance_id, original_instance['temp_id']))

    update_course_instance_ids(created_instances_with_ids)
    return created_instances


def update_course_instance_ids(update_data):
    with connections['coursemanager'].cursor() as cursor:
        update_query = """
            UPDATE temp_courseinstance
            SET course_instance_id = %s
            WHERE id = %s
        """
        cursor.executemany(update_query, update_data)
        connections['coursemanager'].commit()


def update_updated_in_canvas_flag(temp_ids, reverse=False):
    with connections['coursemanager'].cursor() as cursor:
        if reverse:
            update_query = """
                UPDATE temp_courseinstance
                SET updated_in_canvas = 0
                WHERE id = %s
            """
        else:
            update_query = """
                UPDATE temp_courseinstance
                SET updated_in_canvas = 1
                WHERE id = %s
            """
        cursor.executemany(update_query, temp_ids)
        connections['coursemanager'].commit()


def update_course_instance_sync_to_canvas():
    with connections['coursemanager'].cursor() as cursor:
        cursor.execute("SELECT course_instance_id FROM temp_courseinstance WHERE updated_in_canvas=1")
        records = cursor.fetchall()
        for record in records:
            course_instance_id = record[0]
            try:
                course_instance = CourseInstance.objects.get(course_instance_id=course_instance_id)
                course_instance.sync_to_canvas = 1
                course_instance.save()
                logger.debug(f'Enabled sync_to_canvas for ci_id={course_instance.course_instance_id}')
            except CourseInstance.DoesNotExist:
                logger.exception(f'CourseInstance with id={course_instance_id} does not exist')


def _delete_linked_course_instances():
    with connections['coursemanager'].cursor() as cursor:
        cursor.execute("""
            SELECT course_instance_id FROM temp_courseinstance WHERE course_instance_id IS NOT NULL
        """)
        temp_courseinstance_ids = [row[0] for row in cursor.fetchall()]

    if not temp_courseinstance_ids:
        logger.info('No linked CourseInstance records found in temp_courseinstance table.')
        return

    try:
        CourseInstance.objects.filter(id__in=temp_courseinstance_ids).delete()
        logger.debug(f'Deleted {len(temp_courseinstance_ids)} course_instance records')
    except Exception as e:
        logger.exception(f'Error during deletion: {e}')
        with open('delete_db_errors.txt', 'a') as f:
            f.write(f"error={e}" + '\n')
        return

    try:
        with connections['coursemanager'].cursor() as cursor:
            update_query = """
                UPDATE temp_courseinstance SET course_instance_id = NULL WHERE course_instance_id = %s
            """
            cursor.executemany(update_query, [(id,) for id in temp_courseinstance_ids])
            connections['coursemanager'].commit()

            logger.debug(f'Reverted course_instance_id for records')
    except Exception as e:
        logger.exception(f'Error during update: {e}')
        with open('delete_db_errors.txt', 'a') as f:
            f.write(f"error={e}" + '\n')

    return


def reverse():
    # Reverse Canvas update by removing the sis_section_id attached to the section
    instances = get_instances_for_canvas(reverse=True)
    update_canvas_section(instances, reverse=True)

    # Delete the course_instance records associated with the above sections
    _delete_linked_course_instances()
    return
