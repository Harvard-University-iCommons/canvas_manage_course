import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_safe
from django_auth_lti import const
from django_auth_lti.decorators import lti_role_required

from ims_lti_py.tool_config import ToolConfig

from canvas_sdk.methods import enrollments as canvas_api_enrollments
from canvas_sdk.exceptions import CanvasAPIError

from icommons_common.models import Person
from icommons_common.monitor.views import BaseMonitorResponseView
from icommons_common.canvas_api.helpers import (
    courses as canvas_api_helper_courses,
    enrollments as canvas_api_helper_enrollments,
    sections as canvas_api_helper_sections
)

from .utils import (
    SDK_CONTEXT,
    unique_enrollments_not_in_section_filter,
    is_editable_section,
    is_enrollment_section,
    is_sis_section,
    is_credit_status_section,
)


logger = logging.getLogger(__name__)

ENROLLMENT_TYPES = [
    'StudentEnrollment', 'TeacherEnrollment', 'TaEnrollment', 'DesignerEnrollment', 'ObserverEnrollment'
]

LTI_ROLES_PERMITTED = [
    const.ADMINISTRATOR,
    const.CONTENT_DEVELOPER,
    const.INSTRUCTOR,
    const.TEACHING_ASSISTANT,
]


class MonitorResponseView(BaseMonitorResponseView):
    def healthy(self):
        return True


def _filter_student_view_enrollments(enrollments):
    # Filter "Test Student" out of enrollments, "Test Student" is added via the "View as student" feature
    return filter(
        lambda x: x['type'] != settings.MANAGE_SECTIONS.get('TEST_STUDENT_ROLE', 'StudentViewEnrollment'),
        enrollments
    )


def _get_badge_info_for_users(user_id_list):

    logger.debug(
        "getting role types (to display badge info) for the following users: %s"
        % user_id_list
    )

    people = Person.objects.filter(univ_id__in=user_id_list).values_list('univ_id', 'role_type_cd')
    person_id_badge_mapping = {
        univ_id: role_type for univ_id, role_type in people
    }

    logger.debug("IDs found and their role types: %s" % person_id_badge_mapping)

    discrepancies = set(user_id_list) - set(person_id_badge_mapping.keys())
    if discrepancies:
        logger.warn(
            "The following users were not found in COURSEMANAGER "
            "while attempting to get their role types: %s",
            discrepancies
        )

    # If person_id_badge_mapping does not have a result matching user_id
    # (because user_id wasn't found in the Person database above)
    # then send a fake role_type_cd that will return 'other' for badge label
    results_dict = {
        user_id: _get_badge_label_for_role_type(person_id_badge_mapping.get(user_id, "OTHER"))
        for user_id in user_id_list
    }

    logger.debug(
        "found the following badge information for the users: %s" % results_dict
    )
    return results_dict


def _get_badge_label_for_role_type(role_type_cd):
    if role_type_cd in ["STUDENT", "EMPLOYEE", "CLASPART"]:
        return 'HUID'
    elif role_type_cd in ["XIDHOLDER"]:
        return 'XID'
    elif role_type_cd in ["WIDENER", "COUNTWAY"]:
        return 'LIBRARY'
    else:
        return 'OTHER'


def _add_badge_label_name_to_enrollments(enrollments):

    # add custom display badge information for enrollees to the filtered Canvas
    # enrollment objects. Badge information is used to visually distinguish
    # different university ID types / multiple IDs for the same
    # user (i.e. enrollments where the user name is identical)
    user_id_list = [
        (enrollment['user'].get('sis_user_id')) for enrollment in enrollments
    ]
    user_badge_info_mapping = _get_badge_info_for_users(user_id_list)
    for enrollment in enrollments:
        user_id = (enrollment['user'].get('sis_user_id'))
        if user_badge_info_mapping.get(user_id):
            enrollment['badge_label_name'] = user_badge_info_mapping.get(user_id)
    return enrollments


@login_required
@lti_role_required(LTI_ROLES_PERMITTED)
@require_http_methods(['GET'])
def create_section_form(request):
    try:
        canvas_course_id = request.LTI['custom_canvas_course_id']
        course_instance_id = request.LTI['lis_course_offering_sourcedid']
        if course_instance_id == '' or course_instance_id is None:
            logger.error(
                'CID unavailable for course %s' % canvas_course_id
            )
            return render(request, 'manage_sections/error.html', status=500)
        sis_enrollment_section_list = []  # Sections fed from SIS
        section_list = []  # Sections not fed from SIS
        canvas_sections = canvas_api_helper_sections.get_sections(canvas_course_id)
        if not canvas_sections:
            logger.error(
                'No sections found for Canvas course %s' % canvas_course_id
            )
            return render(request, 'manage_sections/error.html', status=500)
        for section in canvas_sections:

            section['enrollment_count'] = len(_filter_student_view_enrollments(section['enrollments']))
            sis_section_id = section.get('sis_section_id')
            if sis_section_id == course_instance_id or sis_section_id == "ci:%s" % course_instance_id:
                # this matches the current course instance id and placed first on the list
                sis_enrollment_section_list.insert(0, section)
            elif is_enrollment_section(sis_section_id) or is_credit_status_section(sis_section_id):
                sis_enrollment_section_list.append(section)
            else:
                if is_sis_section(sis_section_id):
                    section['registrar_section_flag'] = True
                section_list.append(section)

        # case insensitive sort the sections in alpha order
        section_list = sorted(section_list, key=lambda x: x[u'name'].lower())
        
        return render(request, 'manage_sections/create_section_form.html', {
            'sections': section_list,
            'sisenrollmentsections': sis_enrollment_section_list
        })

    except Exception:
        logger.exception('Exception in create_section_form')
        return render(request, 'manage_sections/error.html', status=500)


@login_required
@lti_role_required(LTI_ROLES_PERMITTED)
@require_http_methods(['POST'])
def create_section(request):
    canvas_course_id = request.LTI['custom_canvas_course_id']
    section_name = request.POST.get('section_name_input')

    # check to see if the textbox is empty
    if not section_name or not section_name.strip():
        return render(request, 'manage_sections/create_section_form.html', {}, status=400)

    course_section = canvas_api_helper_sections.create_section(canvas_course_id, section_name.strip())

    # if section creation failed for whatever reason, return error status.
    if not course_section:
        return render(request, 'manage_sections/create_section_form.html', {'section': course_section}, status=500)

    # Append section count to course_section object so the badge will appear correctly. Setting to zero
    # for newly created section.
    course_section['enrollment_count'] = 0

    return render(request, 'manage_sections/section_list.html', {'section': course_section})


@login_required
@lti_role_required(LTI_ROLES_PERMITTED)
@require_http_methods(['POST'])
def edit_section(request, section_id):
    canvas_course_id = request.LTI['custom_canvas_course_id']
    section_name = request.POST.get('section_name_input', '').strip()
    enrollment_count = request.POST.get('enrollment_count')

    # check to see if the textbox is empty
    if not section_name:
        return render(request, 'manage_sections/create_section_form.html', {}, status=400)

    # grab the section
    try:
        section = canvas_api_helper_sections.get_section(canvas_course_id, section_id)
    except RuntimeError:
        logger.exception(
            'Unable to get section {} (course {}) from Canvas'.format(
                section_id, canvas_course_id))
        section = None
    if not section:
        message = 'Failed to retrieve section {} from course {}'.format(section_id, canvas_course_id)
        logger.error(message)
        return JsonResponse({'message': message}, status=500)

    # verify we should allow the edit
    if not is_editable_section(section):
        # send http status code 422=Unprocessable Entity
        return JsonResponse(
            {'message': 'Error: Registrar fed sections cannot be edited'},
            status=422
        )

    # do the edit
    try:
        course_section = canvas_api_helper_sections.update_section(
            canvas_course_id, section_id, course_section_name=section_name
        )
    except RuntimeError:
        logger.exception('Unable to update section {} to {} on Canvas'.format(
            section, section_name))
        course_section = None
    else:
        canvas_api_helper_courses.delete_cache(canvas_course_id=canvas_course_id)
        canvas_api_helper_enrollments.delete_cache(canvas_course_id)

    # if section update failed for whatever reason, return error status.
    if not course_section:
        return render(request, 'manage_sections/create_section_form.html', {},
                      status=500)

    # Append section count to course_section object so the badge will appear
    # correctly. Setting to zero for newly created section.
    course_section['enrollment_count'] = enrollment_count or 0

    return render(request, 'manage_sections/section_list.html',
                  {'section': course_section})


@login_required
@lti_role_required(LTI_ROLES_PERMITTED)
@require_http_methods(['GET'])
def section_details(request, section_id):
    canvas_course_id = request.LTI['custom_canvas_course_id']
    section = canvas_api_helper_sections.get_section(canvas_course_id, section_id)
    if not section:
        logger.error(
            'Section %s not found for Canvas course %s'
            % (section_id, canvas_course_id)
        )
        return render(request, 'manage_sections/error.html', status=500)
    return render(request, 'manage_sections/section_details.html', {
        'section_id': section_id,
        'section_name': section['name'],
        'allow_edit': is_editable_section(section)
    })


@login_required
@lti_role_required(LTI_ROLES_PERMITTED)
@require_http_methods(['GET'])
def section_user_list(request, section_id):
    canvas_course_id = request.LTI['custom_canvas_course_id']
    section = canvas_api_helper_sections.get_section(canvas_course_id, section_id)
    enrollments = _add_badge_label_name_to_enrollments(
        _filter_student_view_enrollments(section['enrollments'])
    )
    enrollments.sort(key=lambda x: x['user']['sortable_name'])
    return render(request, 'manage_sections/_section_userlist.html', {
        'allow_edit': is_editable_section(section),
        'enroll_count': len(enrollments),
        'enrollments': enrollments,
        'section_id': section_id
    })


@login_required
@lti_role_required(LTI_ROLES_PERMITTED)
@require_http_methods(['POST'])
def remove_section(request, section_id):
    canvas_course_id = request.LTI['custom_canvas_course_id']
    section = canvas_api_helper_sections.get_section(canvas_course_id, section_id)
    if not section:
        message = "Failed to retrieve section %s from course %s" % (section_id, canvas_course_id)
        logger.error(message)
        return JsonResponse({'message': message}, status=500)

    if not is_editable_section(section):
        # send http status code 422=Unprocessable Entity
        return JsonResponse(
            {'message': 'Error: Registrar fed sections cannot be deleted'},
            status=422
        )

    section = canvas_api_helper_sections.delete_section(canvas_course_id, section_id)
    if not section:
        message = "Failed to remove section %s from course %s" % (section_id, canvas_course_id)
        logger.error(message)
        return JsonResponse({'message': message}, status=500)

    return JsonResponse(section)


@login_required
@lti_role_required(LTI_ROLES_PERMITTED)
@require_safe
def section_class_list(request, section_id):
    """
    Return a sorted set of enrollments that represent unique combinations of user and role.  Only user/role
    combinations that are not enrolled in the current section are considered.  This view assumes that the
    actual section that the resulting unique enrollments are part of doesn't matter, since this view is used
    to represent the user/role combinations that can be added to the section list.
    """
    canvas_course_id = request.LTI['custom_canvas_course_id']
    section = canvas_api_helper_sections.get_section(canvas_course_id, section_id)
    course_enrollments = [
        e for e in canvas_api_helper_enrollments.get_enrollments(canvas_course_id)
        if e['type'] in ENROLLMENT_TYPES
    ]

    eligible_enrollments = _add_badge_label_name_to_enrollments(
        unique_enrollments_not_in_section_filter(section_id, course_enrollments)
    )
    eligible_enrollments.sort(key=lambda x: x['user']['sortable_name'])

    return render(request, 'manage_sections/_section_classlist.html', {
        'enrollments': eligible_enrollments,
        'section_id': section_id,
        'allow_edit': is_editable_section(section)
    })


@login_required
@lti_role_required(LTI_ROLES_PERMITTED)
@require_http_methods(['POST'])
def add_to_section(request):
    try:
        canvas_course_id = request.LTI['custom_canvas_course_id']
        post_data = json.loads(request.body)
        section_id = post_data['section_id']
        users_to_add = post_data['users_to_add']
    except KeyError:
        message = "Missing post parameters to add users to section_id %s" % request.body
        logger.exception(message)
        return JsonResponse({'success': False, 'message': message}, status=500)

    failed_users = []
    for user in users_to_add:
        try:
            canvas_api_enrollments.enroll_user_sections(
                SDK_CONTEXT,
                section_id,
                user['enrollment_user_id'],
                enrollment_type=user['enrollment_type'],
                enrollment_role=user['enrollment_role'],
                enrollment_enrollment_state='active'
            )
            canvas_api_helper_courses.delete_cache(canvas_course_id=canvas_course_id)
            canvas_api_helper_enrollments.delete_cache(canvas_course_id)
            canvas_api_helper_sections.delete_cache(canvas_course_id)
        except (KeyError, CanvasAPIError):
            logger.exception("Failed to add user to section %s %s", section_id, json.dumps(user))
            failed_users.append(user)

    return JsonResponse({
        'added': len(users_to_add) - len(failed_users),
        'failed': failed_users
    })


@login_required
@lti_role_required(LTI_ROLES_PERMITTED)
@require_http_methods(['POST'])
def remove_from_section(request):
    canvas_course_id = request.LTI['custom_canvas_course_id']
    user_section_id = request.POST.get('user_section_id')
    if not user_section_id:
        return JsonResponse({'message': "Invalid user_section_id %s" % user_section_id}, status=500)
    try:
        response = canvas_api_enrollments.conclude_enrollment(
            SDK_CONTEXT, canvas_course_id, user_section_id, 'delete'
        )
        canvas_api_helper_courses.delete_cache(canvas_course_id=canvas_course_id)
        canvas_api_helper_enrollments.delete_cache(canvas_course_id)
        canvas_api_helper_sections.delete_cache(canvas_course_id)
    except CanvasAPIError:
        message = "Failed to remove user from section %s in course %s", user_section_id, canvas_course_id
        logger.exception(message)
        return JsonResponse({'message': message}, status=500)

    return JsonResponse(response.json())
