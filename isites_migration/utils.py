import logging
import os
import zipfile
import time
import gzip
import json
import ssl
import boto3
import re

from django.conf import settings
from django.db.models import Q
from django.template.loader import get_template
from django.template import Context
from django.db import connections
from icommons_common.models import (
    Topic, FileNode, TopicText, CourseInstance, SiteMap, Course
)
from icommons_common.canvas_utils import SessionInactivityExpirationRC

from canvas_sdk.methods import content_migrations, files
from canvas_sdk.exceptions import CanvasAPIError


logger = logging.getLogger(__name__)
SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)

# Make unverified SSL connections for connecting to Canvas API from tool2.icommons(solaris)
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context


def get_school(course_instance_id, canvas_course_id):
    """
     get the school_id for the course_instance_id or the canvas_course_id provided.
    :param course_instance_id:
    :param canvas_course_id:
    :return school:
    """
    school = None

    try:
        ci = CourseInstance.objects.get(course_instance_id=course_instance_id)
        school = ci.course.school_id
    except CourseInstance.DoesNotExist:
        logger.exception(u'Could not determine the course instance for Canvas '
                         u'course instance id %s' % course_instance_id)
        if canvas_course_id:
            try:
                # get_primary_course_by_canvas_course_id could return None or throw
                # a CourseInstance.DoesNotExist exception
                ci = CourseInstance.objects.get_primary_course_by_canvas_course_id(canvas_course_id)
                if ci:
                    school = ci.course.school_id

            except CourseInstance.DoesNotExist:
                logger.exception(u'Could not determine the primary course instance for Canvas '
                                 u'course id %s', canvas_course_id)
    return school


def _get_archive_title_for_topic(topic):
    if topic['title']:
        topic_title = topic['title'].strip().replace(' ', '_').rstrip('/')
    else:
        topic_title = u'no_title'
    topic_title += "_%d" % topic['topic_id']
    return topic_title


def export_files(keyword):
    s3_bucket = settings.AWS_EXPORT_BUCKET_ISITES_FILES
    logger.info("Beginning iSites file export for keyword %s to S3 bucket %s",
                keyword, s3_bucket)

    # Topics by keyword - iteration returns a simple dict with id and title
    topics = Topic.objects.filter(site__keyword=keyword).exclude(
        Q(tool_id__in=settings.EXPORT_FILES_EXCLUDED_TOOL_IDS) |
        Q(title__in=settings.EXPORT_FILES_EXCLUDED_TOPIC_TITLES)
    ).values('topic_id', 'title')

    # Construct a dict lookup of cleaned up title by topic id
    topic_file_repo_ids = []
    topic_titles_by_id = {}
    for topic in topics:
        topic_id = topic['topic_id']
        topic_title = _get_archive_title_for_topic(topic)
        topic_titles_by_id[topic_id] = topic_title
        topic_file_repo_ids.append("icb.topic%d.files" % topic_id)

    logger.info('Attempting to export files for %d topics', topics.count())
    logger.info("topic_titles_by_id is %s" % topic_titles_by_id)
    logger.info("topic_file_repo_ids is %s" % topic_file_repo_ids)

    file_nodes = FileNode.objects.filter(
        file_type='file', file_repository_id__in=topic_file_repo_ids
    ).select_related('file_repository', 'file_repository__storage_node', 'storage_node')

    topic_texts = TopicText.objects.filter(
        topic_id__in=list(topic_titles_by_id),
        source_text__isnull=False,
    ).only('text_id', 'topic_id', 'name', 'processed_text')

    zip_filename = os.path.join(settings.EXPORT_DIR, "%s%s.zip" %
                                (settings.EXPORT_ARCHIVE_FILENAME_PREFIX, keyword))
    logger.info('Creating zip file %s' % zip_filename)

    # Append to the archive on the fly for file nodes and text
    with zipfile.ZipFile(zip_filename, 'w') as z_file:
        # Export all file nodes
        for file_node in file_nodes:
            # Use some regex magic to extract the numeric topic id from the
            # file repository id (in the form "icb.topic123.files")
            topic_id_str = re.findall(r'\d+', file_node.file_repository_id)[0]
            logger.info("topic id string is %s" % topic_id_str)
            _export_topic_file(
                file_node,
                topic_titles_by_id[int(topic_id_str)],
                z_file
            )
        # Export all text
        for text in topic_texts:
            _export_topic_text(text, topic_titles_by_id[text.topic_id],
                               z_file)

        # Only include the README if defined
        if hasattr(settings, 'EXPORT_FILES_README_FILENAME'):
            _export_readme(keyword, z_file)

        uncompressed_size = sum(info.file_size for info in z_file.infolist())

    logger.info('Uncompressed: %s bytes' % uncompressed_size)

    export_key = "%s.zip" % keyword

    _upload_zip_file_to_s3(zip_filename, s3_bucket, export_key)

    os.remove(zip_filename)

    logger.info("Finished exporting files for keyword %s to S3 bucket %s", keyword, s3_bucket)


def import_files(keyword, canvas_course_id):
    try:
        progress_url = create_canvas_content_migration(keyword, canvas_course_id)

        workflow_state = 'processing'
        while workflow_state not in ['completed', 'failed']:
            time.sleep(2)
            progress = SDK_CONTEXT.session.request('GET', progress_url).json()
            workflow_state = progress['workflow_state']
            if workflow_state == 'completed':
                lock_canvas_folder(canvas_course_id, settings.EXPORT_ARCHIVE_FILENAME_PREFIX + keyword)
    except Exception:
        message = "Failed to complete file import for keyword %s", keyword
        logger.exception(message)
        raise RuntimeError(message)

    return workflow_state


def create_canvas_content_migration(keyword, canvas_course_id):
    try:
        root_folder = _get_root_folder_for_canvas_course(canvas_course_id)
        export_file_url = _get_s3_download_url(settings.AWS_EXPORT_BUCKET_ISITES_FILES,
                                               "%s.zip" % keyword,
                                               settings.AWS_EXPORT_DOWNLOAD_TIMEOUT_SECONDS)
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
        sites = [{'keyword': m.course_site.external_id,
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


def _export_topic_file(file_node, topic_title, zip_file):
    logger.info(u"Exporting file node %s for topic %s",
                file_node.file_node_id, topic_title)
    # There should always be a storage node for topic files, either in the node
    # itself or in the repository
    if file_node.storage_node:
        storage_node_loc = file_node.storage_node.physical_location
    else:
        storage_node_loc = file_node.file_repository.storage_node.physical_location

    # Determine if we're dealing with an fs-docs storage node or an fs-cow
    if 'fs-docs' in storage_node_loc:
        # For pre-COW files, we need to construct the physical file location
        # ourselves
        physical_file_loc = os.path.join(
            file_node.file_repository_id,
            file_node.file_path.lstrip('/'),
            file_node.file_name
        )
    else:
        physical_file_loc = file_node.physical_location.lstrip('/')

    source_file = os.path.join(
        storage_node_loc,
        physical_file_loc
    ).encode('utf8')

    export_file = os.path.join(
        topic_title,
        file_node.file_path.lstrip('/'),
        file_node.file_name
    ).encode('utf8')

    try:
        if file_node.encoding == 'gzip':
            #  Read the whole file as a byte string and write it to the archive
            with gzip.open(source_file, 'rb') as s_file:
                zip_file.writestr(export_file, s_file.read())
        else:
            zip_file.write(source_file, export_file)

        # Encoding source_file so the log string remains a bytestring
        logger.debug("Copied file %s to archive location %s",
                     source_file, export_file)
    except (IOError, OSError):
        logger.exception(
            u"Failed to export file node %d from file repository %s",
            file_node.file_node_id,
            file_node.file_repository_id
        )


def _export_topic_text(topic_text, topic_title, zip_file):
    logger.info(u"Exporting text for topic %d %s",
                topic_text.topic_id, topic_title)

    export_file = os.path.join(
        topic_title,
        topic_text.name.lstrip('/')
    ).encode('utf-8')

    zip_file.writestr(export_file, topic_text.processed_text.encode('utf8'))

    logger.info("Copied TopicText %d to export location %s",
                topic_text.text_id, export_file)


def _export_readme(keyword, zip_file):
    readme_template = get_template('isites_migration/export_files_readme.html')
    content = readme_template.render(Context({}))
    readme_file = settings.EXPORT_FILES_README_FILENAME
    zip_file.writestr(readme_file, content)


def _upload_zip_file_to_s3(filename, s3_bucket, s3_key):
    logger.debug("uploading %s to %s/%s in s3", filename, s3_bucket, s3_key)
    s3 = _get_boto_session().resource('s3')
    s3.meta.client.upload_file(
        filename,
        s3_bucket,
        s3_key,
        ExtraArgs={'ContentType': 'application/zip'}
    )


def _get_boto_session():
    return boto3.session.Session(profile_name=settings.AWS_PROFILE)


def _get_s3_download_url(s3_bucket, s3_key, url_download_timeout_secs):
    logger.debug("generating temporary download url for %s in bucket %s that will be good for %d seconds",
                 s3_bucket, s3_key, url_download_timeout_secs)
    s3 = _get_boto_session().resource('s3')
    url = s3.meta.client.generate_presigned_url(
        "get_object",
        Params={'Bucket': s3_bucket, 'Key': s3_key},
        ExpiresIn=url_download_timeout_secs
    )
    logger.debug("url is %s", url)
    return url


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
