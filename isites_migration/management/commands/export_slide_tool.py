"""
This command is intended to be used with Django settings in
canvas_manage_course.settings.isites_migration
"""

import logging
import os
import mimetypes
import json
import ssl
import boto3

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from icommons_common.models import (
    Site, Topic, FileRepository, FileNode, FileNodeAttribute, ImageMetadata
)


logger = logging.getLogger(__name__)
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context


class Command(BaseCommand):
    help = 'Exports iSites Slide Tool topic file repositories to AWS S3.\n\n' \
           'This command is intended to be used with Django settings in ' \
           'canvas_manage_course.settings.isites_migration.'
    requires_system_checks = True

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.dest_s3_bucket = settings.AWS_EXPORT_BUCKET_SLIDE_TOOL

    def add_arguments(self, parser):
        parser.add_argument('keyword', help='the iSites keyword containing the slide tool to export')
        parser.add_argument('-t', '--tool_id', default=settings.SLIDE_TOOL_ID,
                            help='the iSites slide tool tool_id to use; '
                                 'default is {} (from settings)'
                                 .format(settings.SLIDE_TOOL_ID))

    def handle(self, *args, **options):
        keyword = options['keyword']
        tool_id = options['tool_id']

        logger.info("Beginning export_slide_tool for keyword %s to S3 bucket %s", keyword, self.dest_s3_bucket)

        s3_source_bucket = settings.AWS_SOURCE_BUCKET_ISITES_FILES

        try:
            site = Site.objects.get(keyword=keyword)
        except Site.DoesNotExist:
            raise CommandError('Could not find iSite for the keyword provided.')

        kw = {'aws_access_key_id': settings.ISITES_MIGRATION['aws_access_key_id'],
              'aws_secret_access_key': settings.ISITES_MIGRATION['aws_secret_access_key']}
        try:
            s3 = boto3.session.Session(**kw).resource('s3')
        except:
            logger.exception('Error configuring s3 client')
            raise

        topics = Topic.objects.filter(site__keyword=keyword, tool_id=tool_id)
        for topic in topics:
            logger.info("Exporting files for topic %d %s", topic.topic_id, topic.title)
            topic_data = {
                'keyword': keyword,
                'site_title': site.name,
                'topic_id': topic.topic_id,
                'topic_title': topic.title,
                'files': []
            }
            file_repository_id = "icb.topic%s.files" % topic.topic_id
            try:
                file_repository = FileRepository.objects.get(file_repository_id=file_repository_id)
            except FileRepository.DoesNotExist:
                logger.error("FileRepository does not exist for %s", file_repository_id)
                continue

            for file_node in FileNode.objects.filter(file_repository=file_repository):
                if file_node.file_type == 'file':
                    if file_node.storage_node:
                        storage_node_loc = file_node.storage_node.physical_location
                    elif file_repository.storage_node:
                        storage_node_loc = file_repository.storage_node.physical_location
                    else:
                        logger.error("Failed to find storage node for file node %d", file_node.file_node_id)
                        continue

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
                        physical_file_loc = file_node.physical_location.lstrip(
                            '/')

                    file_name = os.path.basename(physical_file_loc)
                    dest_s3_key = "%s/%d/%s" % (keyword, topic.topic_id, file_name)
                    content_type, _ = mimetypes.guess_type(file_name)
                    s3_extra_args = {}
                    if content_type is not None:
                        s3_extra_args = {'ContentType': content_type}

                    source_file = os.path.join(
                        keyword, storage_node_loc, physical_file_loc
                    ).encode('utf8')

                    source_object_key = source_file[source_file.find('/fsdocs') + 1:]

                    copy_source = {
                        'Bucket': s3_source_bucket,
                        'Key': source_object_key
                    }

                    s3.meta.client.copy(
                        copy_source,
                        self.dest_s3_bucket,
                        dest_s3_key,
                        ExtraArgs=s3_extra_args
                    )
                    logger.info("Copied image to S3 Key %s", dest_s3_key)

                    url = dest_s3_key
                elif file_node.file_type == 'link':
                    try:
                        url = FileNodeAttribute.objects.get(file_node_id=file_node.file_node_id, attribute='url').value
                    except FileNodeAttribute.DoesNotExist:
                        logger.error(
                            "Failed to find URL for file node link %s %s %d",
                            keyword,
                            topic.topic_id,
                            file_node.file_node_id
                        )
                        continue
                else:
                    logger.error("File node %d was not file or link", file_node.file_node_id)
                    continue

                file_data = {
                    'filename': file_node.file_name,
                    'type': file_node.file_type,
                    'url': url
                }

                for im in ImageMetadata.objects.filter(file_node=file_node):
                    field_name = im.topic_metadata_set.metadata_cv.label
                    field_value = im.metadata_data
                    file_data[field_name] = field_value

                topic_data['files'].append(file_data)

            data_key = "%s/%d/data.json" % (keyword, topic.topic_id)
            json_data = json.dumps(topic_data)

            # Store the data.json file with the slide data folder
            s3.Object(self.dest_s3_bucket, data_key).put(
                Body=json_data,
                ContentType='application/json'
            )

            logger.info("Copied file repository data to S3 Key %s", data_key)

        logger.info("Finished export_slide_tool for keyword %s to S3 bucket %s", keyword, self.dest_s3_bucket)
