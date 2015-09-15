import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from async.models import Process

from isites_migration.utils import get_previous_isites_keywords
from isites_migration.jobs import migrate_files


logger = logging.getLogger(__name__)


@login_required
def index(request):
    course_instance_id = request.LTI.get('lis_course_offering_sourcedid')
    canvas_course_id = request.LTI.get('custom_canvas_course_id')
    if request.method == 'POST':
        keyword = request.POST.get('keyword')
        Process.enqueue(
            migrate_files,
            keyword=keyword,
            canvas_course_id=canvas_course_id,
            queue='isites_file_migration'
        )

    processes = Process.objects.filter(name='isites_migration.jobs.migrate_files').order_by('-date_created')
    return render(request, 'isites_migration/index.html', {
        'keywords': get_previous_isites_keywords(course_instance_id),
        'processes': processes
    })
