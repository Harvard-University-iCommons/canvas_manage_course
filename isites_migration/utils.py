import logging
import os
import zipfile
import shutil
import time
import gzip
import json
import ssl

from django.conf import settings
from django.db.models import Q
from django.template.loader import get_template
from django.template import Context
from django.db import connections

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from kitchen.text.converters import to_bytes, to_unicode

from icommons_common.models import (
    Site, Topic, FileRepository, FileNode, TopicText, CourseInstance, SiteMap, Course
)
from icommons_common.canvas_utils import SessionInactivityExpirationRC

from canvas_sdk.methods import content_migrations, files
from canvas_sdk.exceptions import CanvasAPIError


logger = logging.getLogger(__name__)
SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)

# Make unverified SSL connections for connecting to Canvas API from tool2.icommons(solaris)
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context


def export_files(keyword):
    try:
        s3_bucket = _get_s3_bucket(settings.AWS_EXPORT_BUCKET_ISITES_FILES)
        logger.info("Beginning iSites file export for keyword %s to S3 bucket %s", keyword, s3_bucket.name)
        try:
            os.makedirs(os.path.join(settings.EXPORT_DIR, settings.CANVAS_IMPORT_FOLDER_PREFIX + keyword))
        except os.error:
            pass

        site = Site.objects.get(keyword=keyword)

        _export_readme(keyword)

        query_set = Topic.objects.filter(site=site).exclude(
            Q(tool_id__in=settings.EXPORT_FILES_EXCLUDED_TOOL_IDS) |
            Q(title__in=settings.EXPORT_FILES_EXCLUDED_TOPIC_TITLES)
        ).only(
            'topic_id', 'title'
        )
        logger.info('Attempting to export files for %d topics', query_set.count())
        for topic in query_set:
            if topic.title:
                topic_title = topic.title.strip().replace(' ', '_')
            else:
                topic_title = 'no_title_%s' % topic.topic_id

            file_repository_id = "icb.topic%s.files" % topic.topic_id
            try:
                file_repository = FileRepository.objects.select_related('storage_node').only(
                    'file_repository_id', 'storage_node'
                ).get(file_repository_id=file_repository_id)
                _export_file_repository(file_repository, keyword, topic_title)
            except FileRepository.DoesNotExist:
                logger.info("FileRepository does not exist for %s", file_repository_id)
                continue

            _export_topic_text(topic, keyword, topic_title)

        zip_path_index = len(settings.EXPORT_DIR) + 1
        keyword_export_path = os.path.join(settings.EXPORT_DIR, settings.CANVAS_IMPORT_FOLDER_PREFIX + keyword)
        zip_filename = os.path.join(settings.EXPORT_DIR, "%s%s.zip" % (settings.CANVAS_IMPORT_FOLDER_PREFIX, keyword))
        z_file = zipfile.ZipFile(zip_filename, 'w')
        for root, dirs, files in os.walk(keyword_export_path):
            for file in files:
                file_path = os.path.join(root, file)
                z_file.write(file_path, file_path[zip_path_index:])
        z_file.close()

        logger.info('Creating zip file %s' % zip_filename)
        zf_info = zipfile.ZipFile(zip_filename)
        compressed_size = 0
        uncompressed_size = 0
        for z_info in zf_info.infolist():
            compressed_size += z_info.compress_size
            uncompressed_size += z_info.file_size
        z_file.close()

        logger.info('Compressed: %d bytes' % compressed_size)
        logger.info('Uncompressed: %d bytes' % uncompressed_size)

        shutil.rmtree(keyword_export_path)

        export_key = Key(s3_bucket)
        export_key.key = "%s.zip" % keyword
        export_key.set_metadata('Content-Type', 'application/zip')
        export_key.set_contents_from_filename(zip_filename)
        logger.info("Uploaded file export for keyword %s to S3 Key %s", keyword, export_key.key)

        os.remove(zip_filename)

        logger.info("Finished exporting files for keyword %s to S3 bucket %s", keyword, s3_bucket.name)
    except Exception:
        message = "Failed to complete file export for keyword %s", keyword
        logger.exception(message)
        raise RuntimeError(message)


def import_files(keyword, canvas_course_id):
    try:
        progress_url = create_canvas_content_migration(keyword, canvas_course_id)

        workflow_state = 'processing'
        while workflow_state not in ['completed', 'failed']:
            time.sleep(2)
            progress = SDK_CONTEXT.session.request('GET', progress_url).json()
            workflow_state = progress['workflow_state']
            if workflow_state == 'completed':
                lock_canvas_folder(canvas_course_id, settings.CANVAS_IMPORT_FOLDER_PREFIX + keyword)
    except Exception:
        message = "Failed to complete file import for keyword %s", keyword
        logger.exception(message)
        raise RuntimeError(message)

    return workflow_state


def create_canvas_content_migration(keyword, canvas_course_id):
    try:
        root_folder = _get_root_folder_for_canvas_course(canvas_course_id)
        export_file_url = _get_export_s3_url(keyword)
        logger.info("Importing iSites file export from %s to Canvas course %s", export_file_url, canvas_course_id)
        response = content_migrations.create_content_migration_courses(
            SDK_CONTEXT,
            canvas_course_id,
            'zip_file_importer',
            settings_file_url=export_file_url,
            settings_folder_id=root_folder['id']
        ).json()
        progress_url = response['progress_url']
        logger.info(
            "Created Canvas content migration %s for file import from %s to Canvas course %s",
            progress_url,
            export_file_url,
            canvas_course_id
        )
    except Exception:
        message = "Failed to complete file import for keyword %s", keyword
        logger.exception(message)
        raise RuntimeError(message)

    return progress_url


def lock_canvas_folder(canvas_course_id, folder_name):
    import_folder = _get_import_folder(canvas_course_id, folder_name)
    try:
        files.update_folder(
            SDK_CONTEXT,
            import_folder['id'],
            import_folder['name'],
            import_folder['parent_folder_id'],
            None,
            None,
            'true',
            None,
            None
        )
        logger.info("Locked import folder %s for canvas_course_id %s", folder_name, canvas_course_id)
    except CanvasAPIError:
        logger.exception("Failed to lock import folder %s for canvas_course_id %s", folder_name, canvas_course_id)
        raise


def get_previous_isites(course_instance_id):
    """
    Given a course_instance_id, finds iSite keywords mapped to previous offerings of the course

    Adapted from:
    http://subversion.icommons.harvard.edu/filedetails.php?
    repname=Perl.CourseManager&path=%2Fbranches%2Fmod_perl2_2%2Flib%2FCourseTools%2FNewCourseSiteWizard.pm

    :param course_instance_id:
    :return: The list of dicts that contain the keyword, title, and term.
    """
    previous_sites = []
    try:
        course_instance = CourseInstance.objects.get(course_instance_id=course_instance_id)
    except CourseInstance.DoesNotExist:
        return previous_sites

    # Collect the iSites keywords associated with previous offerings of the given course instance
    course = course_instance.course
    previous_instance_ids = {c.course_instance_id for c in course.course_instances.all()}
    # If this is an EXT course, also look for instances where the registrar_code
    # is stored in the registrar_code_display field
    if course.school.school_id == 'ext':
        previous_courses = Course.objects.filter(school=course.school, registrar_code_display=course.registrar_code)
        previous_instance_ids = previous_instance_ids | {
            c.course_instance_id for c in CourseInstance.objects.filter(course__in=previous_courses)
        }

    evm_sql_query = """
    SELECT course_instance_id, user_id
    FROM enrollment_viewer_manager
    WHERE
    course_instance_id = %s
    """
    cursor = connections['termtool'].cursor()

    # Get a list of the enrollment viewer managers for the given course instance
    cursor.execute(evm_sql_query, [course_instance_id])
    evm_user_ids = {user_id for (ci_id, user_id) in cursor.fetchall()}

    # Check each previous offering to verify there is an associated iSite and
    # the course instance's list of enrollment viewer managers intersects
    # with the current course instance's list of enrollment viewer managers
    for previous_instance_id in previous_instance_ids:
        sites = [{'keyword' : m.course_site.external_id,
                  'title': m.course_instance.title,
                  'term': m.course_instance.term.display_name,
                  'calendar_year': m.course_instance.term.calendar_year } for m in SiteMap.objects.filter(
            course_instance_id=previous_instance_id,
            course_site__site_type_id='isite'
        )]
        if sites:
            cursor.execute(evm_sql_query, [previous_instance_id])
            previous_evm_user_ids = {user_id for (ci_id, user_id) in cursor.fetchall()}
            if previous_evm_user_ids & evm_user_ids:
                previous_sites.extend(sites)

    # sort the dicts by calendar_year in descending order
    if previous_sites:
        previous_sites = sorted(previous_sites, key=lambda x: x[u'calendar_year'], reverse=True)

    return previous_sites


def _export_file_repository(file_repository, keyword, topic_title):
    logger.info("Exporting files for file_repository %s", file_repository.file_repository_id)
    query_set = FileNode.objects.filter(
        file_repository=file_repository,
        file_type='file'
    ).select_related('storage_node').only(
        'file_node_id', 'file_type', 'storage_node', 'physical_location', 'file_path', 'file_name', 'encoding'
    )
    for file_node in query_set:
        if file_node.storage_node:
            storage_node_location = file_node.storage_node.physical_location
        elif file_repository.storage_node:
            storage_node_location = file_repository.storage_node.physical_location
        else:
            logger.error("Failed to find storage node for file node %d", file_node.file_node_id)
            continue

        physical_location = file_node.physical_location.lstrip('/')
        if not physical_location:
            # Assume non fs-cow file and use file_path and file_name to construct physical location
            physical_location = os.path.join(
                file_node.file_path.lstrip('/'),
                file_node.file_name.lstrip('/')
            )

        source_file = os.path.join(storage_node_location, physical_location)
        export_file = to_bytes(os.path.join(
            settings.EXPORT_DIR,
            settings.CANVAS_IMPORT_FOLDER_PREFIX + keyword,
            to_unicode(topic_title),
            to_unicode(file_node.file_path.lstrip('/')),
            to_unicode(file_node.file_name.lstrip('/'))
        ))
        try:
            os.makedirs(os.path.dirname(export_file))
        except os.error:
            pass

        if file_node.encoding == 'gzip':
            try:
                with gzip.open(source_file, 'rb') as s_file:
                    with open(export_file, 'w') as d_file:
                        for line in s_file:
                            d_file.write(to_bytes(line, 'utf8'))
            except IOError:
                logger.exception(
                    u"Failed to export file node %d from file repository %d in keyword %s",
                    file_node.file_node_id,
                    file_repository.file_repository_id,
                    keyword
                )
                continue
        else:
            try:
                shutil.copy(source_file, export_file)
            except IOError:
                logger.exception("Could not find source file %s", source_file)
                continue

        logger.info("Copied file %s to export location %s", source_file, export_file)


def _export_topic_text(topic, keyword, topic_title):
    logger.info("Exporting text for topic %d %s", topic.topic_id, topic_title)
    for topic_text in TopicText.objects.filter(topic_id=topic.topic_id).only('text_id', 'name', 'source_text'):
        export_file = to_bytes(os.path.join(
            settings.EXPORT_DIR,
            settings.CANVAS_IMPORT_FOLDER_PREFIX + keyword,
            to_unicode(topic_title),
            to_unicode(topic_text.name.lstrip('/'))
        ))
        try:
            os.makedirs(os.path.dirname(export_file))
        except os.error:
            pass

        with open(export_file, 'w') as f:
            f.write(to_bytes(topic_text.source_text, 'utf8'))

        logger.info("Copied TopicText %d to export location %s", topic_text.text_id, export_file)


def _export_readme(keyword):
    readme_template = get_template('isites_migration/export_files_readme.html')
    content = readme_template.render(Context({}))
    readme_file = os.path.join(
        settings.EXPORT_DIR,
        settings.CANVAS_IMPORT_FOLDER_PREFIX + keyword,
        settings.EXPORT_FILES_README_FILENAME
    )
    try:
        os.makedirs(os.path.dirname(readme_file))
    except os.error:
        pass
    with open(readme_file, 'w') as f:
        f.write(content)


def _get_s3_bucket(bucket_name):
    s3_connection = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_ACCESS_KEY)
    return s3_connection.get_bucket(bucket_name, validate=False)


def _get_export_s3_url(keyword):
    s3_bucket = _get_s3_bucket(settings.AWS_EXPORT_BUCKET_ISITES_FILES)
    key = s3_bucket.get_key("%s.zip" % keyword)
    return key.generate_url(settings.AWS_EXPORT_DOWNLOAD_TIMEOUT_SECONDS)


def _get_root_folder_for_canvas_course(canvas_course_id):
    return files.get_folder_courses(
        SDK_CONTEXT,
        canvas_course_id,
        'root'
    ).json()


def _get_import_folder(canvas_course_id, folder_name):
    root = _get_root_folder_for_canvas_course(canvas_course_id)
    folders = json.loads(files.list_folders(SDK_CONTEXT, root['id']).text)
    import_folder = None
    for folder in folders:
        if folder['name'] == folder_name:
            import_folder = folder
            break
    return import_folder
