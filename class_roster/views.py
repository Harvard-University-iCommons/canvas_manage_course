from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from icommons_common.models import CourseInstance
from lti_school_permissions.decorators import lti_permission_required

logger = logging.getLogger(__name__)

SIS_ROSTER = settings.CLASS_ROSTER['sis_roster']


@login_required
@lti_permission_required('class_roster')
@require_http_methods(['GET'])
def index(request):

    courses = []

    user_id = request.LTI['lis_person_sourcedid']
    course_instance_id = request.LTI['lis_course_offering_sourcedid']

    course_instance = CourseInstance.objects.get(course_instance_id=course_instance_id)
    roster_url = _get_roster_url(course_instance, user_id)
    if roster_url is not None:
        course_title = _get_course_title(course_instance)
        courses.append({'code': course_title, 'url': roster_url})

    for sci in course_instance.secondary_xlist_instances.all():
        roster_url = _get_roster_url(sci, user_id)
        if roster_url is not None:
            course_title = _get_course_title(sci)
            courses.append({'code': course_title, 'url': roster_url})

    return render(request, 'class_roster/index.html', {
        'associated_courses': courses,
        'num_of_courses': len(courses)
    })


def _get_course_title(course_instance):
    course_title = course_instance.short_title if course_instance.short_title != '' else course_instance.title
    if course_title == '':
        course_title = '{} {}'.format(course_instance.course.school_id, course_instance.course.registrar_code)
    if course_instance.section != '':
        course_title = '{} {}'.format(course_title, course_instance.section)

    return course_title


def _get_roster_url(course_instance, user_id):
    cs_strm = course_instance.term.cs_strm
    cs_class_number = course_instance.cs_class_number

    if not cs_strm or not cs_class_number:
        # this course isn't in a my.harvard term or doesn't have a class number
        return None

    dynamic_query = 'INSTRUCTOR_ID={}&CLASS_NBR={}&STRM={}'.format(
        user_id, course_instance.cs_class_number, cs_strm)

    site_url = '{}{}{}{}{}'.format(
        SIS_ROSTER['base_url'],
        SIS_ROSTER['base_path'],
        SIS_ROSTER['static_path'],
        SIS_ROSTER['base_query'],
        dynamic_query)

    return site_url
