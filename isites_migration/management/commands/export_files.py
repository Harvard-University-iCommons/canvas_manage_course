import logging
import csv

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from icommons_common.models import CourseSite

from isites_migration.utils import export_files


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Exports iSites file repositories to AWS S3'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.failures = []

    def add_arguments(self, parser):
        parser.add_argument('--term_id', type=int, help='Provide an SIS term ID')
        parser.add_argument('--keyword', help='Provide an iSites keyword')
        parser.add_argument('--csv', dest='csv_path', help='Provide the path to a csv file containing iSites keyword/Canvas course ID pairs')
        parser.add_argument('--print-keyword-results', action='store_true', help='Print results of a keyword export to stdout')

    def handle(self, *args, **options):
        term_id = options.get('term_id')
        csv_path = options.get('csv_path')
        keyword = options.get('keyword')
        print_results = options.get('print_keyword_results')
        if term_id:
            self._export_term(term_id)
        elif csv_path:
            self._export_csv(csv_path)
        elif keyword:
            self._export_keyword(keyword, print_results)
        else:
            raise CommandError('You must provide one of the --term_id, --keyword, or --csv options.')

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

    def _export_keyword(self, keyword, print_results):
        try:
            export_files(keyword)
            if print_results:
                print "Success|%s.zip" % keyword
        except Exception as e:
            logger.exception("Failed to complete export for keyword %s",
                             keyword)
            raise CommandError("Failed to export %s: %s" % (keyword, str(e)))
