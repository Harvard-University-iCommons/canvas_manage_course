import logging
import os
import mimetypes
import json
import ssl

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from icommons_common.models import (
    Site, Topic, FileRepository, FileNode, FileNodeAttribute, ImageMetadata
)


logger = logging.getLogger(__name__)
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context


class Command(BaseCommand):
    help = 'Exports iSites Slide Tool topic file repositories to AWS S3'
    option_list = BaseCommand.option_list + (
        make_option(
            '--keyword',
            action='store',
            dest='keyword',
            default=None,
            help='Provide an iSite keyword'
        ),
    )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.connection = S3Connection(settings.AWS_ACCESS_KEY_ID, settings.AWS_ACCESS_KEY)
        self.bucket = self.connection.get_bucket(settings.AWS_EXPORT_BUCKET_SLIDE_TOOL, validate=False)

    def handle(self, *args, **options):
        keyword = options['keyword']
        if not keyword:
            # Prompt for iSite keyword
            keyword = raw_input('iSite Keyword: ')
            if not keyword:
                raise CommandError('You must provide an iSite keyword.')

        logger.info("Beginning export_slide_tool for keyword %s to S3 bucket %s", keyword, self.bucket.name)
        try:
            site = Site.objects.get(keyword=keyword)
        except Site.DoesNotExist:
            raise CommandError('Could not find iSite for the keyword provided.')

        topic_sql_query = """
        SELECT t.topic_id AS topic_id, t.title AS title
        FROM topic t, page_content pc, page p, site s
        WHERE
        s.keyword = '%s' AND
        p.site_id = s.site_id AND
        pc.page_id = p.page_id AND
        t.topic_id = pc.topic_id AND
        t.tool_id = %s
        """
        topics = Topic.objects.raw(topic_sql_query, [keyword, settings.SLIDE_TOOL_ID])
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
                        storage_node_location = file_node.storage_node.physical_location
                    elif file_repository.storage_node:
                        storage_node_location = file_repository.storage_node.physical_location
                    else:
                        logger.error("Failed to find storage node for file node %d", file_node.file_node_id)
                        continue

                    file_name = os.path.basename(file_node.physical_location)
                    file_key = Key(self.bucket)
                    file_key.key = "%s/%d/%s" % (keyword, topic.topic_id, file_name)

                    content_type, _ = mimetypes.guess_type(file_name)
                    if content_type is not None:
                        file_key.set_metadata('Content-Type', content_type)
                    file_key.set_contents_from_filename(storage_node_location + file_node.physical_location)
                    logger.info("Uploaded image to S3 Key %s", file_key.key)

                    url = file_key.key
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

            data_key = Key(self.bucket)
            data_key.key = "%s/%d/data.json" % (keyword, topic.topic_id)
            data_key.set_metadata('Content-Type', 'application/json')
            data_key.set_contents_from_string(json.dumps(topic_data))
            logger.info("Uploaded file repository data to S3 Key %s", data_key.key)

        logger.info("Finished export_slide_tool for keyword %s to S3 bucket %s", keyword, self.bucket.name)
