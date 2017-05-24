import errno
import logging
import os
import zipfile
import time
import gzip
import json
import re
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.db.models import Q
from django.template.loader import get_template
from django.template import Context
from django.db import connections
from django.utils.text import get_valid_filename
from canvas_sdk.methods import content_migrations, files

from icommons_common.models import (
    Topic, FileNode, TopicText, CourseInstance, SiteMap, Course
)
from icommons_common.canvas_utils import SessionInactivityExpirationRC

logger = logging.getLogger(__name__)
SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)


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


def _get_topic_text_by_topic_id(topic_ids):
    """Filter topic text on list of topic ids."""
    return TopicText.objects.filter(

        topic_id__in=topic_ids,
        source_text__isnull=False,
    ).only('text_id', 'topic_id', 'name', 'processed_text')


def _get_file_nodes_by_file_repo_id(file_repo_ids):
    """Filter file nodes on list of file repository ids."""
    return FileNode.objects.filter(
        file_type='file', file_repository_id__in=file_repo_ids
    ).select_related('file_repository', 'file_repository__storage_node',
                     'storage_node')


def export_files(keyword):
    """Export iSite archive of files and text to an s3 bucket.  There are 3 file-related
       names we care about: 1) name of zipfile on disk, 2) name of top-level folder in
       the zipfile, and 3) name of file (key) in s3.  We're using the keyword for all
       three of these identifiers now."""
    s3_bucket = settings.AWS_EXPORT_BUCKET_ISITES_FILES
    s3_source_bucket = settings.AWS_SOURCE_BUCKET_ISITES_FILES

    logger.info("Beginning iSites file export for keyword %s to S3 bucket %s",
                keyword, s3_bucket)

    # Topics by keyword - iteration returns a simple dict with id and title
    topics = Topic.objects.filter(site__keyword=keyword).exclude(
        Q(tool_id__in=settings.EXPORT_FILES_EXCLUDED_TOOL_IDS) |
        Q(title__in=settings.EXPORT_FILES_EXCLUDED_TOPIC_TITLES)
    ).values('topic_id', 'title')

    topic_count = topics.count()

    if not topic_count:
        raise Exception("No topics exist for site keyword %s" % keyword)

    logger.info('Attempting to export files and text for %d topics',
                topic_count)

    # Construct a dict lookup of cleaned up title by topic id
    topic_file_repo_ids = []
    topic_titles_by_id = {}
    for topic in topics:
        topic_id = topic['topic_id']
        topic_title = get_valid_filename(topic['title'])
        # Prevent overwriting of files within topics that are named the same
        topic_title += "_%d" % topic_id
        topic_titles_by_id[topic_id] = topic_title
        topic_file_repo_ids.append("icb.topic%d.files" % topic_id)

    _mkdir_p(settings.EXPORT_DIR, 0o755)
    zip_filename = os.path.join(settings.EXPORT_DIR, "%s.zip" % keyword)
    logger.info('Creating zip file %s to store archive' % zip_filename)

    s3 = _get_boto_session().resource('s3').meta.client
    # Write files and text directly to the archive as we go.  Allow for ZIP64
    # extension to accomodate zip files > 2GB
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_STORED, True) as z_file:
        # Export all files
        for file_node in _get_file_nodes_by_file_repo_id(topic_file_repo_ids):
            # Use some regex magic to extract the numeric topic id string
            # from the file repository id (i.e. "icb.topic123.files")
            # http://stackoverflow.com/questions/10365225
            topic_id_str = re.findall(r'\d+', file_node.file_repository_id)[0]
            logger.debug("topic id for file node %d is %s",
                         file_node.file_node_id, topic_id_str)
            _export_topic_file(file_node, topic_titles_by_id[int(topic_id_str)],
                               keyword, z_file, s3, s3_source_bucket)
        # Export all text
        for text in _get_topic_text_by_topic_id(list(topic_titles_by_id)):
            _export_topic_text(text, topic_titles_by_id[text.topic_id],
                               keyword, z_file)

        # Only include the README if defined
        readme_filename = getattr(settings, 'EXPORT_FILES_README_FILENAME', None)
        if readme_filename is not None:
            _export_readme(keyword, z_file, readme_filename)

    # Calculate the size of the archive for log purposes
    uncompressed_size = os.stat(zip_filename).st_size

    logger.info('Uncompressed: %s bytes' % uncompressed_size)

    _upload_zip_file_to_s3(zip_filename, s3_bucket, "%s.zip" % keyword)

    os.remove(zip_filename)  # Cleanup the archive on disk

    logger.info("Finished exporting files for keyword %s to S3 bucket %s",
                keyword, s3_bucket)

    return ("%s.zip", uncompressed_size)


def import_files(keyword, canvas_course_id):
    progress_url = create_canvas_content_migration(keyword, canvas_course_id)

    workflow_state = 'processing'
    while workflow_state not in ['completed', 'failed']:
        time.sleep(2)
        progress = SDK_CONTEXT.session.request('GET', progress_url).json()
        workflow_state = progress['workflow_state']
        if workflow_state == 'completed':
            lock_canvas_folder(canvas_course_id, keyword)
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
    except Exception:
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
        previous_sites = sorted(previous_sites, key=lambda x: x[u'calendar_year'],
                                reverse=True)

    return previous_sites


def _export_topic_file(file_node, topic_title, keyword, zip_file, s3, source_bucket):
    logger.debug(u"Exporting file node %s for topic %s",
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
        keyword, storage_node_loc, physical_file_loc
    ).encode('utf8')

    export_file = os.path.join(
        keyword, topic_title, file_node.file_path.lstrip('/'),
        file_node.file_name
    ).encode('utf8')

    object_key = source_file[source_file.find('/fsdocs')+1:]

    try:
        isites_doc = s3.get_object(Bucket=source_bucket, Key=object_key)
        if file_node.encoding == 'gzip':
            #  Read the whole file as a byte string and write it to the archive
            bytestream = BytesIO(isites_doc['Body'].read())
            file_content = gzip.GzipFile(None, 'rb', fileobj=bytestream).read()
            zip_file.writestr(export_file, file_content)
        else:
            zip_file.writestr(export_file, isites_doc['Body'].read())

        # Encoding source_file so the log string remains a bytestring
        logger.debug("Copied file %s to archive location %s",
                     source_file, export_file)
    except (IOError, OSError, ClientError):
        logger.exception(
            u"Failed to export file node %d from file repository %s using "
            u"source bucket %s and s3 object key %s",
            file_node.file_node_id,
            file_node.file_repository_id,
            source_bucket,
            object_key
        )


def _export_topic_text(topic_text, topic_title, keyword, zip_file):
    logger.debug(u"Exporting text for topic %d %s",
                 topic_text.topic_id, topic_title)

    # Prevent overwriting of text with same name within a topic by
    # prepending topic text id.
    topic_text_filename = "%d_%s" % (topic_text.text_id,
                                     get_valid_filename(topic_text.name))

    # Processed topic text is HTML, so append the .html extension if not already
    # present
    if not topic_text_filename.endswith(".html"):
        topic_text_filename += ".html"

    export_file = os.path.join(
        keyword,
        topic_title,
        topic_text_filename,
    ).encode('utf-8')

    zip_file.writestr(export_file, topic_text.processed_text.encode('utf8'))

    logger.debug("Copied TopicText %d to export location %s",
                 topic_text.text_id, export_file)


def _export_readme(keyword, zip_file, readme_filename):
    logger.debug("Exporting readme file for keyword %s", keyword)
    readme_template = get_template('isites_migration/export_files_readme.html')
    content = readme_template.render(Context({}))
    zip_file.writestr(os.path.join(keyword, readme_filename), content)
    logging.debug("Copied Readme file to export location %s", readme_filename)


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
    return boto3.session.Session(
        aws_access_key_id=settings.ISITES_MIGRATION['aws_access_key_id'],
        aws_secret_access_key=settings.ISITES_MIGRATION['aws_secret_access_key'])


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


# see http://stackoverflow.com/a/600612
def _mkdir_p(path, mode=0o777):
    try:
        os.makedirs(path, mode)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
