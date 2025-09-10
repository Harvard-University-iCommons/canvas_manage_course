import json
import logging
import re
import time

from canvas_api.helpers import courses as canvas_api_helper_courses
from canvas_api.helpers import enrollments as canvas_api_helper_enrollments
from canvas_api.helpers import sections as canvas_api_helper_sections
from canvas_sdk.exceptions import CanvasAPIError
from canvas_sdk.methods import enrollments as canvas_api_enrollments
from canvas_sdk.methods import users as canvas_api_users
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_safe
from icommons_common.models import (CourseEnrollee, CourseGuest,
                                    CourseInstance, CourseStaff, Person,
                                    UserRole)
from icommons_common.monitor.views import BaseMonitorResponseView
from lti_school_permissions.decorators import lti_permission_required

from .utils import (SDK_CONTEXT, create_db_section, delete_enrollments,
                    is_credit_status_section, is_editable_section,
                    is_enrollment_section, is_sis_section,
                    unique_enrollments_not_in_section_filter)

logger = logging.getLogger(__name__)

ENROLLMENT_TYPES = [
    'StudentEnrollment', 'TeacherEnrollment', 'TaEnrollment', 'DesignerEnrollment', 'ObserverEnrollment'
]


class MonitorResponseView(BaseMonitorResponseView):
    def healthy(self):
        return True


def _filter_student_view_enrollments(enrollments):
    # Filter "Test Student" out of enrollments, "Test Student" is added via the "View as student" feature
    return [x for x in enrollments if x['type'] != settings.MANAGE_SECTIONS.get('TEST_STUDENT_ROLE', 'StudentViewEnrollment')]


def _get_badge_info_for_users(user_id_list):

    logger.debug(
        "getting role types (to display badge info) for the following users: %s"
        % user_id_list
    )

    if not user_id_list:
        return {}

    people = Person.objects.raw(_get_people_in_list_query(user_id_list))
    person_id_badge_mapping = {
        p.univ_id: p.role_type_cd for p in people
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
@lti_permission_required('manage_sections')
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

        # fetch total_students_size for the course
        kwargs = {}
        kwargs['include'] = 'total_students'
        start = time.time()
        course = canvas_api_helper_courses.get_course(canvas_course_id, **kwargs)
        logger.debug('Total time for get_course is ={} for course {}'.format(time.time() - start, canvas_course_id))
        total_students_size = 0
        if course:
            if 'total_students' not in course:
                logger.debug('total_students not in cached object, flushing and refetching object..')
                # this is probably  a cached object without the count. Clear the cache object and re-fetch the course
                canvas_api_helper_courses.delete_cache(canvas_course_id=canvas_course_id)
                course = canvas_api_helper_courses.get_course(canvas_course_id, **kwargs)

            if course and 'total_students' in course:
                total_students_size = course['total_students']

        logger.debug('total_students_size={}'.format(total_students_size))

        canvas_sections = canvas_api_helper_sections.get_sections(canvas_course_id, fetch_enrollments=False)

        if not canvas_sections:
            logger.error(
                'No sections found for Canvas course %s' % canvas_course_id
            )
            return render(request, 'manage_sections/error.html', status=500)

        for section in canvas_sections:
            if 'total_students' in section:
                section['enrollment_count'] = section['total_students']
            else:
                section['enrollment_count'] = 'n/a'

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
        section_list = sorted(section_list, key=lambda x: x['name'].lower())

        return render(request, 'manage_sections/create_section_form.html', {
            'sections': section_list,
            'sisenrollmentsections': sis_enrollment_section_list
        })

    except Exception:
        logger.exception('Exception in create_section_form')
        return render(request, 'manage_sections/error.html', status=500)


@login_required
@lti_permission_required('manage_sections')
@require_http_methods(['POST'])
def create_section(request):
    canvas_course_id = request.LTI['custom_canvas_course_id']
    section_name = request.POST.get('section_name_input')
    course_instance_id = request.LTI['lis_course_offering_sourcedid']

    # check to see if the textbox is empty
    if not section_name or not section_name.strip():
        return render(request, 'manage_sections/create_section_form.html', {}, status=400)

    # get parent course instance
    try:
        parent_course_instance = CourseInstance.objects.get(course_instance_id=course_instance_id)
    except Exception as e:
        logger.exception(f'Exception in edit_section: {e}')
        return render(request, 'manage_sections/error.html', status=500)

    try:
        created_db_section = create_db_section(parent_course_instance, section_name)
    except Exception as e:
        logger.exception(f'Exception in create_section: {e}')
        return render(request, 'manage_sections/error.html', status=500)

    canvas_course_section = canvas_api_helper_sections.create_section(canvas_course_id, section_name.strip(), sis_section_id=created_db_section.course_instance_id)

    # Append section count to course_section object so the badge will appear correctly. Setting to zero
    # for newly created section.
    canvas_course_section['enrollment_count'] = 0

    return render(request, 'manage_sections/section_list.html', {'section': canvas_course_section})


@login_required
@lti_permission_required('manage_sections')
@require_http_methods(['POST'])
def edit_section(request, sis_section_id, section_id):
    canvas_course_id = request.LTI['custom_canvas_course_id']
    section_name = request.POST.get('section_name_input', '').strip()
    enrollment_count = request.POST.get('enrollment_count')

    # check to see if the textbox is empty
    if not section_name:
        return render(request, 'manage_sections/create_section_form.html', {}, status=400)

    # verify we should allow the edit
    if not is_editable_section(sis_section_id):
        # send http status code 422=Unprocessable Entity
        return JsonResponse(
            {'message': 'Error: Registrar fed sections cannot be edited'},
            status=422
        )

    # grab the section from the db
    try:
        section = CourseInstance.objects.get(course_instance_id=sis_section_id)
    except Exception as e:
        logger.exception(f'Exception in edit_section: {e}')
        return render(request, 'manage_sections/error.html', status=500)

    if not section:
        message = 'Failed to retrieve section {} from course {}'.format(sis_section_id, canvas_course_id)
        logger.error(message)
        return JsonResponse({'message': message}, status=500)

    # Make the edit in the DB
    try:
        section.title = section_name
        section.short_title = section_name
        section.save()
    except Exception as e:
        logger.exception(f'Exception in edit_section: {e}')
        return render(request, 'manage_sections/create_section_form.html', {}, status=500)

    # Now attempt the edit via Canvas API
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

    # Append section count to course_section object so the badge will appear
    # correctly. Setting to zero for newly created section.
    course_section['enrollment_count'] = enrollment_count or 0

    return render(request, 'manage_sections/section_list.html',
                  {'section': course_section})


@login_required
@lti_permission_required('manage_sections')
@require_http_methods(['GET'])
def section_details(request, section_id, sis_section_id):
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
        'sis_section_id': sis_section_id,
        'allow_edit': is_editable_section(section)
    })


@login_required
@lti_permission_required('manage_sections')
@require_http_methods(['GET'])
def section_user_list(request, section_id):
    canvas_course_id = request.LTI['custom_canvas_course_id']
    section = canvas_api_helper_sections.get_section(canvas_course_id, section_id)
    enrollments_raw = _filter_student_view_enrollments(section['enrollments'])
    enrollments_badged = _add_badge_label_name_to_enrollments(enrollments_raw)
    enrollments = canvas_api_helper_enrollments.add_role_labels_to_enrollments(
        enrollments_badged)
    enrollments.sort(key=lambda x: x['user']['sortable_name'])
    return render(request, 'manage_sections/_section_userlist.html', {
        'allow_edit': is_editable_section(section),
        'enroll_count': len(enrollments),
        'enrollments': enrollments,
        'section_id': section_id
    })


@login_required
@lti_permission_required('manage_sections')
@require_http_methods(['POST'])
def remove_section(request, sis_section_id, section_id):
    canvas_course_id = request.LTI['custom_canvas_course_id']

    canvas_section = canvas_api_helper_sections.get_section(canvas_course_id, section_id)
    if not canvas_section:
        message = f"Failed to retrieve section {section_id} from course {canvas_course_id}"
        logger.error(message)
        return JsonResponse({'message': message}, status=500)

    if not is_editable_section(canvas_section):
        # send http status code 422=Unprocessable Entity
        return JsonResponse(
            {'message': 'Error: Registrar fed sections cannot be deleted'},
            status=422
        )

    # grab the section from the db
    try:
        db_section = CourseInstance.objects.get(course_instance_id=sis_section_id)
        db_section.deleted = 1
        db_section.sync_to_canvas = 0
        db_section.save()
    except Exception as e:
        logger.exception(f'Error retrieving section {sis_section_id} for deletion: {e}')
        return render(request, 'manage_sections/error.html', status=500)

    # Now check/delete enrollments
    for table in (CourseEnrollee, CourseGuest, CourseStaff):
        try:
            enrollments = table.objects.filter(course_instance_id=sis_section_id).delete()
        except Exception as e:
            message = f'Error retrieving enrollments for section {sis_section_id} for deletion: {e}'
            logger.error(message)
            return JsonResponse({'message': message}, status=500)

    enrollments = canvas_api_enrollments.list_enrollments_sections(SDK_CONTEXT, section_id).json()
    if len(enrollments) > 0:
        # delete enrollments before deleting section
        responses, is_empty = delete_enrollments(enrollments, canvas_course_id)
        if not is_empty:
            return JsonResponse({
                'message': f'Issue clearing enrollments prior to deletion. Unable to delete section {section_id} from course {canvas_course_id}'},
                status=500
            )

    canvas_section = canvas_api_helper_sections.delete_section(canvas_course_id, section_id)
    return JsonResponse(canvas_section)


@login_required
@lti_permission_required('manage_sections')
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

    # Fetch enrollments for the course
    course_enrollments = [
        e for e in canvas_api_helper_enrollments.get_enrollments(canvas_course_id)
        if e['type'] in ENROLLMENT_TYPES
    ]

    # Apply the unique enrollment filter, ensuring non-manual enrollments are included
    eligible_enrollments = unique_enrollments_not_in_section_filter(
        section_id, course_enrollments)

    # Add badges and roles to the filtered enrollments
    enrollments_badged = _add_badge_label_name_to_enrollments(
        eligible_enrollments)
    enrollments = canvas_api_helper_enrollments.add_role_labels_to_enrollments(
        enrollments_badged)

    enrollments.sort(key=lambda x: x['user']['sortable_name'])

    return render(request, 'manage_sections/_section_classlist.html', {
        'enrollments': enrollments,
        'section_id': section_id,
        'allow_edit': is_editable_section(section)
    })


@login_required
@lti_permission_required('manage_sections')
@require_http_methods(['POST'])
def add_to_section(request):
    try:
        canvas_course_id = request.LTI['custom_canvas_course_id']
        post_data = json.loads(request.body)
        section_id = post_data['section_id']
        sis_section_id = post_data['sis_section_id']
        users_to_add = post_data['users_to_add']
    except KeyError:
        message = f"Missing post parameters to add users to section_id {request.body}"
        logger.exception(message)
        return JsonResponse({'success': False, 'message': message}, status=500)

    # Map Canvas role to DB role
    for user in users_to_add:
        # The user is a student, but we have 5 roles that map to 90 in the DB, so
        # select the one designated purely as Student
        try:
            if user['enrollment_role_id'] == '90':
                db_role = UserRole.objects.get(role_id=0)
            else:
                db_role = UserRole.objects.get(canvas_role_id=user['enrollment_role_id'])
        except Exception as e:
            message = f"Failed to retrieve role {user['enrollment_role_id']} from DB: {e}"
            logger.exception(message)
            return JsonResponse({'success': False, 'message': message}, status=500)

        # get the user's HUID from Canvas
        try:
            huid = canvas_api_users.get_user_profile(SDK_CONTEXT, user['enrollment_user_id']).json()['sis_user_id']
        except Exception as e:
            message = f"Failed to retrieve user {user['enrollment_user_id']} from Canvas: {e}"
            logger.exception(message)
            return JsonResponse({'success': False, 'message': message}, status=500)

        if db_role.staff == '1':
            table = CourseStaff
        elif db_role.student == '1':
            table = CourseEnrollee
        else:
            table = CourseGuest

        try:
            enrollment = table(
                course_instance_id=sis_section_id,
                user_id = huid,
                role = db_role,
                source='managecrs'
            )
            enrollment.save()
        except Exception as e:
            message = f"Failed to add user {user['enrollment_user_id']} to DB: {e}"
            logger.exception(message)
            return JsonResponse({'success': False, 'message': message}, status=500)

    # Make a best-effort attempt to add the user to the section in Canvas.
    # If this fails, we'll proceed anyway knowing that the feed will
    # eventually add the user to the section
    failed_users = []
    for user in users_to_add:
        try:
            canvas_api_enrollments.enroll_user_sections(
                SDK_CONTEXT,
                section_id,
                user['enrollment_user_id'],
                enrollment_type=user['enrollment_type'],
                enrollment_role_id=user['enrollment_role_id'],
                enrollment_enrollment_state='active'
            )
        except (KeyError, CanvasAPIError):
            logger.exception(f"Failed to add user to section {section_id} {json.dumps(user)}")
            failed_users.append(user)
    canvas_api_helper_courses.delete_cache(canvas_course_id=canvas_course_id)
    canvas_api_helper_enrollments.delete_cache(canvas_course_id)
    canvas_api_helper_sections.delete_cache(canvas_course_id)
    canvas_api_helper_sections.delete_section_cache(section_id)

    return JsonResponse({
        'added': len(users_to_add) - len(failed_users),
        'failed': failed_users
    })


@login_required
@lti_permission_required('manage_sections')
@require_http_methods(['POST'])
def remove_from_section(request):
    canvas_course_id = request.LTI['custom_canvas_course_id']
    user_section_id = request.POST.get('user_section_id')
    sis_section_id = request.POST.get('sis_section_id')
    section_id = request.POST.get('section_id')
    role_id = request.POST.get('role_id')
    user_id = request.POST.get('user_id')
    if not user_section_id:
        return JsonResponse({'message': f"Invalid user_section_id {user_section_id}"}, status=500)

    # Get HUID from Canvas
    try:
        huid = canvas_api_users.get_user_profile(SDK_CONTEXT, user_id).json()['sis_user_id']
    except Exception as e:
        message = f"Failed to retrieve user profile info for user {user_id} from Canvas: {e}"
        logger.exception(message)
        return JsonResponse({'success': False, 'message': message}, status=500)

    # There are 5 roles that map to 90 in the DB, so select the one designated purely as Student.
    try:
        if role_id == '90':
            db_role = UserRole.objects.get(role_id=0)
        else:
            db_role = UserRole.objects.get(canvas_role_id=role_id)
    except Exception as e:
        message = f"Failed to retrieve role {role_id} from DB: {e}"
        logger.exception(message)
        return JsonResponse({'success': False, 'message': message}, status=500)

    if db_role.staff == '1':
        table = CourseStaff
    elif db_role.student == '1':
        table = CourseEnrollee
    else:
        table = CourseGuest

    try:
        table.objects.get(course_instance_id=int(sis_section_id), user_id=huid, role=db_role).delete()
        logger.info(f'Successfully deleted user_id={huid}, role={db_role} from course_instance_id={int(sis_section_id)}')
    except Exception as e:
        message = f"Failed to retrieve enrollment record for section {sis_section_id} from DB: {e}"
        logger.exception(message)
        return JsonResponse({'success': False, 'message': message}, status=500)

    # Now delete from Canvas
    try:
        response = canvas_api_enrollments.conclude_enrollment(
            SDK_CONTEXT, canvas_course_id, user_section_id, 'delete'
        )
        canvas_api_helper_courses.delete_cache(canvas_course_id=canvas_course_id)
        canvas_api_helper_enrollments.delete_cache(canvas_course_id)
        canvas_api_helper_sections.delete_cache(canvas_course_id)
        canvas_api_helper_sections.delete_section_cache(section_id)

    except CanvasAPIError:
        message = f"Failed to remove user from section {user_section_id} in course {canvas_course_id}"
        logger.exception(message)
        canvas_api_helper_sections.delete_cache(canvas_course_id)
        return JsonResponse({'message': message}, status=500)

    return JsonResponse(response.json())


def _get_people_in_list_query(user_id_list=[]):
    pat = re.compile(r'[^\w-]+', re.UNICODE)
    clean_user_ids = ["'{}'".format(pat.sub('', i)) for i in user_id_list if len(pat.sub('', i)) <= 10]
    if clean_user_ids:
        # split clean_user_ids into chunks of 999 (https://www.geeksforgeeks.org/break-list-chunks-size-n-python/)
        n = 999
        chunks = [clean_user_ids[i * n:(i + 1) * n] for i in range((len(clean_user_ids) + n - 1) // n )]

        # create the raw query with one of the chunks
        raw_person_query = 'select * from people.v_huid_and_xid_people where univ_id in ({})'.format(','.join(chunks.pop()))
        # if there are remaining chunks, add them to the where clause
        for chunk in chunks:
            raw_person_query += ' or univ_id in ({})'.format(','.join(chunk))
        logger.debug(raw_person_query)
        return raw_person_query
