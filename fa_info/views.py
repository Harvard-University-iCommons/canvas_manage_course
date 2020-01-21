from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from icommons_common.models import CourseInstance
from lti_school_permissions.decorators import lti_permission_required

@login_required
@lti_permission_required('fa_info')
@require_http_methods(['GET'])
def index(request):
    """ Returns a redirect to the course's FAINFO page """
    course_instance_id = request.LTI['lis_course_offering_sourcedid']
    course_instance = CourseInstance.objects.get(course_instance_id=course_instance_id)
    
    term_id = course_instance.term.cs_strm
    course_id = course_instance.course.registrar_code
    url = "https://portal.my.harvard.edu/psp/hrvihprd/EMPLOYEE/HRMS/c/HU_FINAL"\
        "_ASSMNT.HU_FINAL_ASSMNT.GBL?Page=HU_EXAM_ROSTER_INS&Action=U&ExactKey"\
        "s=Y&INSTITUTION=HRVRD&ACAD_CAREER=FAS&STRM={}&CRSE_ID={}".format(term_id, course_id)
    if not term_id or not course_id:
        return render(request, 'fa_info/index.html')
    return redirect(url)
 
 
