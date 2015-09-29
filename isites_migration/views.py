import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from lti_permissions.decorators import lti_permission_required
from async.models import Process

from isites_migration.utils import get_previous_isites_keywords
from isites_migration.jobs import migrate_files


logger = logging.getLogger(__name__)


@login_required
@lti_permission_required(settings.PERMISSION_ISITES_MIGRATION_IMPORT_FILES)
def index(request):
    course_instance_id = request.LTI.get('lis_course_offering_sourcedid')
    canvas_course_id = request.LTI.get('custom_canvas_course_id')
    if request.method == 'POST':
        keyword = request.POST.get('keyword')
        Process.enqueue(
            migrate_files,
            'isites_file_migration',
            keyword=keyword,
            canvas_course_id=canvas_course_id
        )
        return redirect('isites_migration:index')

    processes = Process.objects.filter(
        name='isites_migration.jobs.migrate_files',
        details__at_canvas_course_id=canvas_course_id
    ).order_by('-date_created')

    has_active_process = len([p for p in processes if p.state != Process.COMPLETE]) > 0
    return render(request, 'isites_migration/index.html', {
        'keywords': get_previous_isites_keywords(course_instance_id),
        'processes': processes,
        'has_active_process': has_active_process
    })
