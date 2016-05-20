import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from lti_permissions.decorators import lti_permission_required
from async.models import Process
from icommons_common.models import CourseInstance
from isites_migration.utils import get_previous_isites, get_school
from isites_migration.jobs import migrate_files


logger = logging.getLogger(__name__)


@login_required
@lti_permission_required(settings.CUSTOM_LTI_PERMISSIONS['isites_migration'])
def index(request):

    course_instance_id = request.LTI.get('lis_course_offering_sourcedid')
    canvas_course_id = request.LTI.get('custom_canvas_course_id')

    if request.method == 'POST':
        keyword = request.POST.get('keyword')
        title = request.POST.get('title')
        term = request.POST.get('term')
        school = None
        Process.enqueue(
            migrate_files,
            'isites_file_migration',
            keyword=keyword,
            canvas_course_id=canvas_course_id,
            term=term,
            title=title
        )

        # try to get the school.
        # if we have a course instance id, try that first.
        school = get_school(course_instance_id, canvas_course_id)

        logger.info(u'"migration started" %s %s "%s" "%s" %s %s %s' % (request.user.username, keyword, title, term,
                                                                 course_instance_id, canvas_course_id, school))
        return redirect('isites_migration:index')

    processes = Process.objects.filter(
        name='isites_migration.jobs.migrate_files',
        details__at_canvas_course_id=canvas_course_id
    ).order_by('-date_created')

    has_active_process = len([p for p in processes if p.state != Process.COMPLETE]) > 0
    return render(request, 'isites_migration/index.html', {
        'isites': get_previous_isites(course_instance_id),
        'processes': processes,
        'link_to_files_page': settings.CANVAS_URL + '/courses/%s/files' % canvas_course_id,
        'has_active_process': has_active_process,
        # Harcode to EST for now, but eventually set based on the launch user's profile setting
        'user_timezone': 'America/New_York',
    })
