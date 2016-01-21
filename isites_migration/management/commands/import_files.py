import logging
import csv
import time

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from icommons_common.canvas_utils import SessionInactivityExpirationRC

from isites_migration.utils import create_canvas_content_migration, lock_canvas_folder


logger = logging.getLogger(__name__)
SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)


class Command(BaseCommand):
    help = 'Imports iSites file repository export to Canvas'
    option_list = BaseCommand.option_list + (
        make_option(
            '--keyword',
            action='store',
            dest='keyword',
            default=None,
            help='Provide an iSites keyword'
        ),
        make_option(
            '--canvas_course_id',
            action='store',
            dest='canvas_course_id',
            default=None,
            help='Provide a Canvas course ID'
        ),
        make_option(
            '--csv',
            action='store',
            dest='csv_path',
            default=None,
            help='Provide the path to a csv file containing iSites keyword/Canvas course ID pairs'
        ),
    )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.canvas_progress_urls = {}

    def handle(self, *args, **options):
        keyword = options.get('keyword')
        canvas_course_id = options.get('canvas_course_id')
        csv_path = options.get('csv_path')

        if csv_path:
            self._import_csv(csv_path)
        elif keyword and canvas_course_id:
            self._import_isite(keyword, canvas_course_id)
        else:
            raise CommandError(
                'You must provide either the --keyword and --canvas_course_id options or the --csv option.'
            )

        import_count = len(self.canvas_progress_urls)
        completed = set()
        failed = set()
        while self.canvas_progress_urls:
            time.sleep(2)
            completed_imports = []
            failed_imports = []
            for keyword, (canvas_course_id, progress_url) in self.canvas_progress_urls.iteritems():
                progress = SDK_CONTEXT.session.request('GET', progress_url).json()
                workflow_state = progress['workflow_state']
                if workflow_state == 'completed':
                    lock_canvas_folder(canvas_course_id, settings.EXPORT_ARCHIVE_FILENAME_PREFIX + keyword)
                    completed_imports.append((keyword, canvas_course_id))
                elif workflow_state == 'failed':
                    failed_imports.append((keyword, canvas_course_id))

            for (keyword, canvas_course_id) in completed_imports + failed_imports:
                self.canvas_progress_urls.pop(keyword, None)

            completed.update(completed_imports)
            failed.update(failed_imports)
            count_processing = len(self.canvas_progress_urls)
            if count_processing:
                logger.info(
                    "%d Canvas imports complete, %d failed, %d processing",
                    len(completed),
                    len(failed),
                    count_processing
                )

        logger.info(
            "Completed import of %d iSites file exports, %d successful %d failed.",
            import_count,
            len(completed),
            len(failed)
        )
        for (keyword, canvas_course_id) in completed:
            logger.info("%s:%s successful", keyword, canvas_course_id)
        for (keyword, canvas_course_id) in failed:
            logger.info("%s:%s failed", keyword, canvas_course_id)

    def _import_csv(self, csv_path):
        logger.info("Importing iSites file exports from csv %s", csv_path)
        try:
            with open(csv_path, 'rU') as csv_file:
                for row in csv.reader(csv_file):
                    self._import_isite(row[0], row[1])
        except (IOError, IndexError):
            raise CommandError("Failed to read csv file %s", csv_path)

    def _import_isite(self, keyword, canvas_course_id):
        progress_url = create_canvas_content_migration(keyword, canvas_course_id)
        self.canvas_progress_urls.append(progress_url)
