import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from async.models import Process

from icommons_common.models import CourseInstance, SiteMap

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

    try:
        course_instance = CourseInstance.objects.get(course_instance_id=course_instance_id)
        course_instance_ids = [c.course_instance_id for c in course_instance.course.course_instances.all()]
        keywords = [m.course_site.external_id for m in SiteMap.objects.filter(
            course_instance_id__in=course_instance_ids,
            course_site__site_type_id='isite'
        )]
    except CourseInstance.DoesNotExist:
        keywords = []

    processes = Process.objects.filter(name='isites_migration.jobs.migrate_files').order_by('-date_created')
    return render(request, 'isites_migration/index.html', {
        'keywords': keywords,
        'processes': processes
    })
