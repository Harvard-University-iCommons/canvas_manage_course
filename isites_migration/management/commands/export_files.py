import logging
import csv

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from icommons_common.models import CourseSite

from isites_migration.utils import export_files


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Exports iSites file repositories to AWS S3'
    option_list = BaseCommand.option_list + (
        make_option(
            '--term_id',
            action='store',
            dest='term_id',
            default=None,
            help='Provide an SIS term ID'
        ),
        make_option(
            '--keyword',
            action='store',
            dest='keyword',
            default=None,
            help='Provide an iSites keyword'
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
        self.failures = []

    def handle(self, *args, **options):
        term_id = options.get('term_id')
        csv_path = options.get('csv_path')
        keyword = options.get('keyword')
        if term_id:
            self._export_term(term_id)
        elif csv_path:
            self._export_csv(csv_path)
        elif keyword:
            self._export_keyword(keyword)
        else:
            raise CommandError('You must provide one of the --term_id, --keyword, or --csv options.')

        if self.failures:
            logger.error("Failed to export files for keywords: %s", self.failures)

    def _export_term(self, term_id):
        keyword_sql_query = """
        SELECT cs.external_id AS external_id
        FROM course_instance ci, site_map sm, course_site cs
        WHERE
        ci.term_id = %d AND
        sm.course_instance_id = ci.course_instance_id AND
        sm.map_type_id = 'official' AND
        sm.course_site_id = cs.course_site_id AND
        cs.site_type_id = 'isite';
        """
        for cs in CourseSite.objects.raw(keyword_sql_query, [term_id]):
            self._export_keyword(cs.external_id)

    def _export_csv(self, csv_path):
        try:
            with open(csv_path, 'rU') as csv_file:
                for row in csv.reader(csv_file):
                    keyword = row[0]
                    self._export_keyword(keyword)
        except (IOError, IndexError):
            raise CommandError("Failed to read csv file %s", csv_path)

    def _export_keyword(self, keyword):
        try:
            export_files(keyword)
        except RuntimeError:
            logger.exception("Failed to complete export for keyword %s", keyword)
            self.failures.append(keyword)
