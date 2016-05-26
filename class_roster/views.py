from __future__ import unicode_literals
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
import requests

from lti_permissions.decorators import lti_permission_required

logger = logging.getLogger(__name__)

SIS_ROSTER = settings.CLASS_ROSTER['sis_roster']


@login_required
@lti_permission_required(settings.CUSTOM_LTI_PERMISSIONS['class_roster'])
@require_http_methods(['GET'])
def index(request):

    courses = []

    user_id = request.LTI['lis_person_sourcedid']
    course_instance_id = request.LTI['lis_course_offering_sourcedid']

    course_instances = _get_course_instances(course_instance_id)
    for course_instance in course_instances:
        roster_url = _get_roster_url(course_instance, user_id)
        if roster_url is not None:
            course_title = _get_course_title(course_instance)
            courses.append({'code': course_title, 'url': roster_url})

    return render(request, 'class_roster/index.html', {
        'associated_courses': courses,
        'num_of_courses': len(courses)
    })


def _get_course_title(course_instance):
    section = str(course_instance.get('section', '')).strip()
    short_title = str(course_instance.get('short_title', '')).strip()
    registrar_code = str(
        course_instance.get('course', {}).get('registrar_code', '')).strip()
    school_id = str(
        course_instance.get('course', {}).get('school_id', '')).strip().upper()
    title = str(course_instance.get('title', '')).strip()

    course_title = short_title if short_title != '' else title
    if course_title == '':
        course_title = '{} {}'.format(school_id, registrar_code)
    if section != '':
        course_title = '{} {}'.format(course_title, section)

    return course_title


def _get_roster_url(course_instance, user_id):
    calendar_year = str(
        course_instance.get('term', {}).get('calendar_year', '')).strip()
    # cs_class_number can be None or blank
    cs_class_number = course_instance.get('cs_class_number', '')
    cs_class_number = str(cs_class_number).strip() if cs_class_number is not None else ''
    term_code = str(
        course_instance.get('term', {}).get('term_code', '')).strip()
    if calendar_year == '' or cs_class_number == '' or term_code == '':
        logger.error('Class roster tool cannot build a my.harvard class roster'
                     ' link for course instance {}, as it is missing required '
                     ' information: calendar_year={}; cs_class_number={};'
                     ' term_code={}', course_instance, calendar_year,
                     cs_class_number, term_code)
        return None  # we cannot build a link for this course instance; skip it

    cs_term_code = '{}{}{}'.format(calendar_year[0],  # [y]yyy
                                   calendar_year[-2:],  # yy[yy]
                                   term_code)

    dynamic_query = 'INSTRUCTOR_ID={}&CLASS_NBR={}&STRM={}'.format(
        user_id, cs_class_number, cs_term_code)

    site_url = '{}{}{}{}{}'.format(
        SIS_ROSTER['base_url'],
        SIS_ROSTER['base_path'],
        SIS_ROSTER['static_path'],
        SIS_ROSTER['base_query'],
        dynamic_query)

    return site_url


def _get_course_instances(primary_course_instance_id):
    """
    returns primary course instance and all secondary xlisted course instances
    """

    base_path = '/api/course/v2/'
    request_args = {
        'params': {
            'format': 'json',
            'include': 'xlist_instances',
        },
        'headers': {
            'Authorization': "Token {}".format(settings.ICOMMONS_REST_API_TOKEN)
        },
        'verify': settings.ICOMMONS_REST_API_SKIP_CERT_VERIFICATION
    }

    path = 'course_instances/{}/'.format(primary_course_instance_id)
    url = '{}{}{}'.format(settings.ICOMMONS_REST_API_HOST, base_path, path)
    response = requests.get(url, **request_args)
    if response.status_code != 200:
        logger.error(
            'Cannot generate a class roster link for course instance {}. '
            'API response (status {}): {}'.format(
                primary_course_instance_id, response.status_code, response.text)
        )
        return []

    # Assume we're on a primary course, and look for any secondary xlisted
    # courses that may exist.
    # We don't need to worry about the case where we're in the Canvas site
    # of a secondary course -- only admins will have access to those; there
    # is no AC to handle that case.
    primary_course_instance = response.json()
    if str(primary_course_instance.get('course_instance_id', '')).strip() == '':
        logger.error(
            'Cannot generate a class roster link for course instance {}. '
            'API response: {}'.format(primary_course_instance_id, response.text)
        )
        return []

    courses = [primary_course_instance]
    for secondary in primary_course_instance['secondary_xlist_instances']:
        courses.append(secondary)

    return courses
