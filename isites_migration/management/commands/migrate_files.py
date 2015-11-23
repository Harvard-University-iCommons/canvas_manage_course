import logging

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate iSites file repositories to Canvas'
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

    def handle(self, *args, **options):
        keyword = options.get('keyword')
        canvas_course_id = options.get('canvas_course_id')
        csv_path = options.get('csv_path')

        if csv_path:
            call_command('export_files', csv_path=csv_path)
            call_command('import_files', csv_path=csv_path)
        elif keyword and canvas_course_id:
            call_command('export_files', keyword=keyword, canvas_course_id=canvas_course_id)
            call_command('import_files', keyword=keyword, canvas_course_id=canvas_course_id)
        else:
            raise CommandError(
                'You must provide either the --keyword and --canvas_course_id options or the --csv option.'
            )
