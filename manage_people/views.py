import json
import logging
import pprint
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

from canvas_sdk.exceptions import CanvasAPIError
from canvas_sdk.methods import enrollments
from canvas_sdk.utils import get_all_list_data
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from icommons_common.canvas_api.helpers import \
    courses as canvas_api_helper_courses
from icommons_common.canvas_api.helpers import \
    enrollments as canvas_api_helper_enrollments
from icommons_common.canvas_api.helpers import \
    sections as canvas_api_helper_sections
from icommons_common.canvas_api.helpers.roles import get_roles_for_account_id
from icommons_common.canvas_utils import (SessionInactivityExpirationRC,
                                          add_canvas_course_enrollee,
                                          add_canvas_section_enrollee,
                                          get_canvas_course_section)
from icommons_common.models import (CourseEnrollee, CourseGuest,
                                    CourseInstance, CourseStaff, Person,
                                    UserRole)
from lti_school_permissions.decorators import lti_permission_required

from manage_people.utils import (get_available_roles, get_canvas_role_name,
                                 get_canvas_to_user_role_id_map,
                                 get_course_member_class,
                                 get_user_role_if_permitted)

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)

COURSE_MEMBER_CLASSES = (CourseEnrollee, CourseGuest, CourseStaff)

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger('manage_people_audit_log')
pp = pprint.PrettyPrinter(indent=4)


@login_required
@require_http_methods(['GET'])
def find_user(request):
    return render(request, 'manage_people/find_user.html', {})


@login_required
@lti_permission_required('manage_people')
@require_http_methods(['GET'])
def user_form(request):
    # display the form to find a user
    try:
        course_instance_id = request.LTI['lis_course_offering_sourcedid']
        canvas_course_id = request.LTI['custom_canvas_course_id']
        canvas_host = request.LTI['custom_canvas_api_domain']
    except KeyError as e:
        return lti_key_error_response(request, e)

    if not CourseInstance.objects.filter(pk=course_instance_id).exists():
        return render(request, 'manage_people/user_form.html', {
            'canvas_course_id': canvas_course_id,
            'canvas_host': canvas_host,
            'not_found': True,
        })

    # get section users added through the tool(filter out the users added via
    # sis import feed)
    filtered_enrollments = get_enrollments_added_through_tool(course_instance_id)
    return render(request, 'manage_people/user_form.html', {
        'canvas_course_id': canvas_course_id,
        'canvas_host': canvas_host,
        'filtered_enrollments': filtered_enrollments,
        'lbl_message': 'good',
    })


@login_required
@lti_permission_required('manage_people')
@require_http_methods(['GET'])
def results_list(request):
    """ Display the list of matches; let the user select one or more """
    search_term = request.GET['user_search_term'].strip()
    try:
        course_instance_id = request.LTI['lis_course_offering_sourcedid']
        canvas_course_id = request.LTI['custom_canvas_course_id']
        canvas_host = request.LTI['custom_canvas_api_domain']
    except KeyError as e:
        return lti_key_error_response(request, e)

    # flesh out any errors sent from the client (?)
    errors = request.GET.get('errors')
    error_messages = []
    if errors:
        error_messages = [settings.MANAGE_PEOPLE['MSGS'].get(error)
                          for error in errors.split(',')]

    # show the find_user page if there was no search term
    if not search_term:
        return render(request, 'manage_people/find_user.html', {
            'canvas_course_id': course_instance_id,
            'canvas_host': canvas_host,
            'error_message': 'Nothing',
            'filtered_enrollments': get_enrollments_added_through_tool(
                                        course_instance_id),
            'lbl_message': 'error',
        })

    # audit all searches for a given ID, regardless of whether they are
    # successful for now, this includes typos (see TLT-876)
    audit_logger.info(
        "User=%s searched for user with query string='%s' for"
        "canvas_course_id=%s",
        request.user.username, search_term, canvas_course_id)

    # show the find_user page if the search came up empty
    search_results = find_person(search_term)
    if not search_results:
        return render(request, 'manage_people/find_user.html', {
            'canvas_course_id': canvas_course_id,
            'canvas_host': canvas_host,
            'filtered_enrollments': get_enrollments_added_through_tool(
                                        course_instance_id),
            'notfound': 'true',
            'search_term': search_term,
        })

    # Find all users enrolled in the course according to Canvas with roles that
    # are deletable via Manage People.
    available_roles = get_available_roles(course_instance_id)
    enrolled_roles_by_id = get_enrolled_roles_for_user_ids(
        canvas_course_id, list(search_results.keys()))
    user_ids_with_enrollments = list(enrolled_roles_by_id.keys())

    # If there is was a found enrollment for the searched user, capture the
    # first/last name for use in the template
    found_person = None
    for univ_id in user_ids_with_enrollments:
        if univ_id in search_results:
            # TODO - some kind of heuristic on which person record to prefer
            found_person = search_results[univ_id]
            break

    # unique results list contains search results minus the userids with
    # existing roles (to prevent additional roles from being added for the
    # same userid - TLT-1101)
    unique_results = {
        user_id: person
        for user_id, person in list(search_results.items())
        if user_id not in user_ids_with_enrollments
    }

    return render(request, 'manage_people/results_list.html', {
        'available_roles': available_roles,
        'enrolled_roles_by_id': dict(enrolled_roles_by_id),  # templates don't
                                                             # like defaultdicts
        'error_messages': error_messages,
        'found_person': found_person,
        'results': search_results,
        'unique_results': unique_results,
        'user_search_term': search_term,
    })


def get_enrolled_roles_for_user_ids(canvas_course_id, search_results_user_ids):
    """
    Look for any ids returned from the search query that match ids already
    enrolled in the course.  If we find a match, add them to the found_ids.
    This list will be used in the template to disable the checkbox for ids that
    are already enrolled in the course and to display Canvas role names.
    Do not match XIDs.
    """
    t0 = time.perf_counter()
    logger.debug(f'search_results_user_ids: {search_results_user_ids}')
    canvas_enrollments = []
    for user_id in search_results_user_ids:
        try:
            canvas_enrollments.extend(
                get_all_list_data(SDK_CONTEXT, enrollments.list_enrollments_courses, canvas_course_id, user_id=f'sis_user_id:{user_id}', per_page=100)
            )
        except:
            logger.exception(f'Canvas API returned an error when searching for enrollments for {user_id}. That user may not exist in Canvas at all.')
    t1 = time.perf_counter()
    logger.debug(f'canvas_enrollments: {canvas_enrollments}')
    logger.debug(f'*** TIMING list_enrollments_courses took {t1 - t0} seconds')

    # get the updated (or cached) Canvas role list so we can show the right
    # role labels for these enrollments
    canvas_roles_by_role_id = get_roles_for_account_id('self')
    t2 = time.perf_counter()
    logger.debug(f'*** TIMING get_roles_for_account_id took {t2 - t1} seconds')

    found_ids = defaultdict(list)
    for enrollment in canvas_enrollments:
        try:
            sis_user_id = enrollment['user']['sis_user_id']
        except KeyError:
            continue
        else:
            if sis_user_id in search_results_user_ids:
                enrollment.update(
                    {'canvas_role_label': canvas_roles_by_role_id[
                        enrollment['role_id']]['label']})
                found_ids[sis_user_id].append(enrollment)

    t3 = time.perf_counter()
    logger.debug(f'*** TIMING getting role labels took {t3 - t2} seconds')
    return found_ids

def find_person(search_term):
    t0 = time.perf_counter()
    if "@" in search_term:
        # treat it as an email address
        filter_kvp = {'email_address__iexact': search_term}
    else:
        # treat it as a user id
        filter_kvp = {'univ_id__iexact': search_term}

    person_results = Person.objects.filter(**filter_kvp)
    t1 = time.perf_counter()
    logger.debug(f'*** TIMING Person filter took {t1 - t0} seconds')
    if len(person_results) == 0:
        logger.info('Search term %s was not found.', search_term)

    results_dict = {}
    for person in person_results:
        person.badge_label_name = get_badge_label_name(person.role_type_cd)
        # Identify which custom CSS label to use
        person.mycustom = person.badge_label_name.lower()
        results_dict[person.univ_id] = person
    t2 = time.perf_counter()
    logger.debug(f'*** TIMING getting badge label names took {t2 - t1} seconds')
    return results_dict


def get_badge_info_for_users(user_id_list=None):
    t0 = time.perf_counter()
    # TODO: documentation and line-by-line comments and remove unused code
    logger.debug('getting role types (to display badge info) for the following '
                 'users: %s', user_id_list)
    if not user_id_list:
        return {}

    people = Person.objects.raw(_get_people_in_list_query(user_id_list))
    person_id_badge_mapping = {
        p.univ_id: p.role_type_cd for p in people
    }

    logger.debug("IDs found and their role types: %s", person_id_badge_mapping)

    discrepancies = set(user_id_list) - set(person_id_badge_mapping.keys())
    if discrepancies:
        logger.warn("The following users were not found in COURSEMANAGER while "
                    "attempting to get their role types: %s", discrepancies)

    # If person_id_badge_mapping does not have a result matching user_id
    # (because user_id wasn't found in the Person database above) then send a
    # fake role_type_cd that will return 'other' for badge label
    results_dict = {
        user_id: get_badge_label_name(person_id_badge_mapping.get(user_id,
                                                                  "OTHER"))
            for user_id in user_id_list
    }

    logger.debug("found the following badge information for the users: %s",
                 results_dict)
    t1 = time.perf_counter()
    logger.debug(f'*** TIMING get_badge_info_for_users took {t1 - t0} seconds')
    return results_dict


@login_required
@lti_permission_required('manage_people')
@require_http_methods(['POST'])
def add_users(request):
    """
    Add user enrollments for selected users/roles
    """
    try:
        canvas_course_instance_id = request.LTI['custom_canvas_course_id']
        course_instance_id = request.LTI['lis_course_offering_sourcedid']
    except KeyError as e:
        return lti_key_error_response(request, e)

    search_term = request.POST.get('user_search_term').strip()
    users_to_add = json.loads(request.POST.get('users_to_add', '{}'))

    if not users_to_add:
        kwargs = {
            'user_search_term': search_term,
            'errors': 'no_user_selected',
        }
        return HttpResponseRedirect(
            "%s?%s" % (reverse('manage_people:results_list'), urllib.parse.urlencode(kwargs))
        )

    course = canvas_api_helper_courses.get_course(canvas_course_instance_id)
    workflow_state = course['workflow_state']

    # For each selected user id, attempt to create an enrollment
    enrollment_results = []
    for user_id, user_role_id in list(users_to_add.items()):
        # Add the returned (existing_enrollment, person) tuple to the results
        # list
        enrollment_results.append(
            add_member_to_course(user_id, int(user_role_id), course_instance_id,
                                 canvas_course_instance_id))

    # get the updated (or cached) Canvas role list so we can show the right
    # role labels for these enrollments
    canvas_roles_by_role_id = get_roles_for_account_id('self')
    user_roles = list(UserRole.objects.values())
    labels_by_user_role_id = {
        role['role_id']: canvas_roles_by_role_id[
            int(role['canvas_role_id'])]['label']
        for role in user_roles
        if role.get('canvas_role_id')
        and canvas_roles_by_role_id.get(
            int(role['canvas_role_id'])
        )
    }

    # annotate enrollments with the Canvas role label
    for (_, person) in enrollment_results:
        person.canvas_role_label = labels_by_user_role_id.get(person.role_id)

    return render(request, 'manage_people/add_user_confirmation.html', {
        'workflow_state': workflow_state,
        'enrollment_results': enrollment_results,
        'person': enrollment_results[0][1],
    })


def add_member_to_course(user_id, user_role_id, course_instance_id,
                         canvas_course_id):
    """
    Returns a (existing_enrollment, person) tuple, existing_enrollment is true
    if there was already an existing enrollment for the given user/role
    """

    user_role = get_user_role_if_permitted(course_instance_id, user_role_id)
    if user_role is None:
        return False, None

    # get an instance of the correct Course* model class for this role
    model_class = get_course_member_class(user_role)
    enrollment = model_class()

    # populate and store the enrollment in coursemanager
    enrollment.user_id = user_id
    enrollment.role_id = user_role_id
    enrollment.course_instance_id = course_instance_id
    logger.debug('Adding %s to %s table as user_role_id %s',
                 user_id, enrollment._meta.db_table, user_role_id)
    existing_enrollment = False
    try:
        enrollment.save()
    except IntegrityError as e:
        existing_enrollment = True
        logger.exception(
            f'Unable to save user {user_id} to table {enrollment._meta.db_table} '
            f'as user_role_id {user_role_id} in course instance {course_instance_id}'
        )
    except RuntimeError as e:
        existing_enrollment = True
        logger.exception(
            f'Unexpected error while saving user {user_id} to table {enrollment._meta.db_table} '
            f'as user_role_id {user_role_id} in course instance {course_instance_id}'
        )

    # get and annotate a Person instance for this enrollment
    person = Person.objects.filter(univ_id=user_id)[0]
    person.badge_label = get_badge_label_name(person.role_type_cd)
    person.role_id = user_role.role_id
    person.role_name = user_role.role_name

    # create the canvas enrollment if needed.  add enrollee to primary section
    # if it exists, otherwise add to the course.
    if not existing_enrollment:
        # TODO: both add_canvas_*_enrollee calls expect (and pass to the api)
        #       a role label.  the api docs show that as deprecated, and the
        #       preferred approach is to pass the role id.  we should do that.
        #       punted for now so we don't need to do another icommons_common
        #       release. Those helpers are used elsewhere, as well, so there are
        #       refactoring implications. We could use the SDK or the REST API
        #       in the future.
        canvas_role_name = get_canvas_role_name(user_role_id)
        canvas_section = get_canvas_course_section(course_instance_id)
        if canvas_section:
            canvas_enrollment = add_canvas_section_enrollee(
                canvas_section['id'], canvas_role_name, user_id, enrollment_role_id=user_role.canvas_role_id)
        else:
            canvas_enrollment = add_canvas_course_enrollee(
                canvas_course_id, canvas_role_name, user_id, enrollment_role_id=user_role.canvas_role_id)

        if canvas_enrollment:
            # flush the canvas api caches on successful enrollment
            canvas_api_helper_courses.delete_cache(
                canvas_course_id=canvas_course_id)
            canvas_api_helper_enrollments.delete_cache(canvas_course_id)
            canvas_api_helper_sections.delete_cache(canvas_course_id)
        else:
            logger.error(
                f'Unable to enroll {user_id} as user_role_id {user_role_id} '
                f'(Canvas role id {user_role.canvas_role_id}) for course instance id {course_instance_id}.'
            )
    return existing_enrollment, person


def get_enrollments_added_through_tool(sis_course_id):
    """
    This method fetches the primary section enrollments for this course and
    then filters out the course enrollees that are fed via sis import feed
    process or cross-registration.
    """
    t0 = time.perf_counter()
    logger.debug('*** TIMING get_enrollments_added_through_tool(course_instance_id=%s)',
                 sis_course_id)

    section_id_param = 'sis_section_id:' + str(sis_course_id)
    try:
        canvas_enrollments = get_all_list_data(
                SDK_CONTEXT, enrollments.list_enrollments_sections,
                section_id_param)
    except CanvasAPIError as api_error:
        logger.error(
            'CanvasAPIError in get_all_list_data call for sis_course_id=%s. '
            'Exception=%s:', sis_course_id, api_error)
        return []
    logger.debug("size of enrollees in canvas= %s" % len(canvas_enrollments))
    t1 = time.perf_counter()
    logger.debug(f'*** TIMING list_enrollments_sections took {t1 - t0} seconds')
    # get the list of enrolles from Course Manager DB, who are eligible to be
    # deleted via this tool.  This is achieved by using a filter to exclude
    # users with values equal to e.g. 'xmlfeed','fasfeed', or 'xreg_map' in the
    # 'SOURCE' column, which indicates that these users were fed from the
    # registrar feed or xreg.  Note: The code is excluding any source containing
    # 'feed' to capture various feed sources like 'xmlfeed','fasfeed','icfeed'
    # etc.

    eligible_ids = set()
    query = (Q(course_instance_id=sis_course_id) &
             (Q(source__isnull=True) |
              ~(Q(source__icontains='feed') | Q(source='xreg_map'))))
    for model in COURSE_MEMBER_CLASSES:
        ids = None
        try:
            ids = list(model.objects.filter(query).values_list('user_id',
                                                               'role_id'))
        except Exception as e:
            logger.exception('unable to look up course members in %s: %s',
                             model._meta.db_table, e)
        else:
            logger.debug('eligible %s members = %s',
                         model._meta.db_table, ids)
        if ids:
            eligible_ids.update(ids)
    logger.debug('full set of eligible user/role ids: %s', eligible_ids)
    t2 = time.perf_counter()
    logger.debug(f'*** TIMING looking up eligible course members took {t2 - t1} seconds')

    # get a mapping of canvas role_id to UserRole ids
    canvas_role_to_user_role = get_canvas_to_user_role_id_map()
    t3 = time.perf_counter()
    logger.debug(f'*** TIMING looking up get_canvas_to_user_role_id_map took {t3 - t2} seconds')
    logger.debug(f'canvas_role_to_user_role: {canvas_role_to_user_role}')

    # get the updated (or cached) Canvas role list so we can show the right
    # Canvas role labels for the enrollments
    canvas_roles_by_role_id = get_roles_for_account_id('self')
    t4 = time.perf_counter()
    # Further filter users to remove users who may not yet be be in canvas.
    # For the moment we are treating COURSEMANAGER as the single source of truth
    # for who should be enrolled in a course, but we also need to get Canvas
    # enrollee attributes like enrollee_id, which is required for deleting the
    # user further on. Hence we disallow deletion of anyone who's not also
    # accurately represented in Canvas.

    filtered_enrollments = []
    for enrollment in canvas_enrollments:
        logger.debug(f'looking at canvas enrollment {enrollment}')
        if enrollment.get('user'):
            # If sis_user_id exists, use it; if not, use login_id; if neither
            # exist then log it and do not include
            user_id = (enrollment['user'].get('sis_user_id') or
                           enrollment['user'].get('login_id'))
            user_role_id = canvas_role_to_user_role[enrollment['role_id']]
            if user_id and (user_id, user_role_id) in eligible_ids:
                logger.debug(f'looking up enrollment {user_id} role_id {enrollment.get("role_id")} in canvas_roles_by_role_id')
                enrollment.update({
                    'user_role_id': user_role_id,
                    'canvas_role_label': canvas_roles_by_role_id.get(
                        enrollment['role_id'], {}).get('label', f'Unknown role {enrollment["role_id"]}')})
                filtered_enrollments.append(enrollment)
                logger.debug('MP filter out registrar fed: Allowing (%s, %s)',
                             user_id, user_role_id)
            else:
                # Log the users not yet in Canvas or who do not match because
                # they're missing an sis_user_id or login_id.  These users will
                # not be available for removal in the tool. Assumes all users
                # have sortable_name and assumes sis_user_id is the source of
                # truth in Canvas (see comment above re:TLT-705)
                logger.info(
                    'Manage People: Canvas %s (Canvas role_id %s, '
                    'user_role_id %s) enrollment for user %s (CM user id %s) '
                    'was either not found in the Coursemanager DB, or was '
                    'registrar-fed.  Not including it in the results list.',
                    enrollment['role'],
                    enrollment['role_id'],
                    canvas_role_to_user_role[enrollment['role_id']],
                    enrollment['user'].get('sortable_name'),
                    enrollment['user'].get('sis_user_id'))
        else:
            # Problem with canvas enrollee data structure
            logger.info(
                'Manage People: Canvas enrollment does not have user '
                'information associated with it. Enrollment info: %s',
                enrollment)
    t5 = time.perf_counter()
    logger.debug(f'*** TIMING filtering enrollments took {t5 - t4} seconds')

    # Sort the users by sortable_name
    filtered_enrollments.sort(key=lambda x: x['user']['sortable_name'])
    logger.debug('size of filtered and sorted enrollments= %s',
                 len(filtered_enrollments))
    t6 = time.perf_counter()

    # add custom display badge information for enrollees to the filtered
    # Canvas enrollment objects badge information is used on user_form to
    # identify different university ID types and distinguish  multiple IDs
    # for the same user (i.e. enrollments where the user name is identical)
    user_id_list = [enrollment['user'].get('sis_user_id')
                        for enrollment in filtered_enrollments]
    user_badge_info_mapping = get_badge_info_for_users(user_id_list)
    t7 = time.perf_counter()
    logger.debug(f'*** TIMING getting badge info for users took {t7 - t6} seconds')
    # user_badge_info_mapping = {}
    for enrollment in filtered_enrollments:
        user_id = enrollment['user'].get('sis_user_id')
        if user_id and user_id in user_badge_info_mapping:
            enrollment['badge_label_name'] = user_badge_info_mapping[user_id]
        # Check if the given enrollment can be deleted in the current tool
        # If it can not, we want to disable the delete option in the template
        t6_1 = time.perf_counter()
        user_role = get_user_role_if_permitted(sis_course_id, enrollment['user_role_id'])
        t6_2 = time.perf_counter()
        logger.debug(f'*** TIMING get_user_role_if_permitted {t6_2 - t6_1} seconds')
        enrollment['can_be_deleted'] = True if user_role is not None else False
    t8 = time.perf_counter()
    logger.debug(f'*** TIMING getting can_be_deleted took {t8 - t7} seconds')
    return filtered_enrollments


@login_required
@lti_permission_required('manage_people')
@require_http_methods(['POST'])
def remove_user(request):
    canvas_course_id = request.POST.get('canvas_course_id')
    sis_user_id = request.POST.get('sis_user_id')
    canvas_role_id = request.POST.get('canvas_role_id')
    user_role_id = request.POST.get('user_role_id')
    try:
        course_instance_id = request.LTI['lis_course_offering_sourcedid']
    except KeyError as e:
        return lti_key_error_response(request, e)

    user_role = get_user_role_if_permitted(course_instance_id, user_role_id)
    if user_role is None:
        return JsonResponse(
            {'result': 'failure',
             'message': 'Error: The specified user role {} is not valid.'
                 .format(user_role_id)},
            status=500)

    if int(user_role.canvas_role_id) != int(canvas_role_id):
        logger.exception(
            'The specified Canvas role %s does not correspond with user role '
            '%s record\'s Canvas role (%s).', canvas_role_id, user_role_id,
            user_role.canvas_role_id)
        return JsonResponse(
            {'result': 'failure',
             'message': 'Error: The specified canvas role {} is not valid.'
                 .format(canvas_role_id)},
            status=500)

    # start by getting all the enrollments for this user
    user_id = 'sis_user_id:%s' % sis_user_id
    try:
        user_enrollments = get_all_list_data(
                SDK_CONTEXT, enrollments.list_enrollments_users, user_id)
    except CanvasAPIError as api_error:
        logger.exception(
            "CanvasAPIError trying to get enrollments for user %s",
            sis_user_id, api_error)
        return JsonResponse(
            {'result': 'failure',
             'message': 'Error: There was a problem getting enrollments for '
                        'the user.'},
            status=500)
    else:
        # create a filtered list of just the users enrollments for the course
        # matching the canvas_course_id and the canvas role being removed
        user_enrollments_to_remove = [
            enrollment['id'] for enrollment in user_enrollments
                if (int(enrollment['course_id']) == int(canvas_course_id)
                    and int(enrollment['role_id']) == int(canvas_role_id))]

    # Remove the user from all Canvas sections in course
    for enrollment_id in user_enrollments_to_remove:
        try:
            enrollments.conclude_enrollment(SDK_CONTEXT, canvas_course_id,
                                            enrollment_id, task='delete')
        except CanvasAPIError as api_error:
            logger.exception(
                'Canvas API Error trying to delete user %s with enrollment id '
                '%s from course instance %s: %s',
                sis_user_id, enrollment_id, course_instance_id, api_error
            )
            return JsonResponse(
                {'result': 'failure',
                 'message': 'Error: There was a problem in deleting the user'},
                status=500)

    # update canvas api caches
    canvas_api_helper_courses.delete_cache(canvas_course_id=canvas_course_id)
    canvas_api_helper_enrollments.delete_cache(canvas_course_id)
    canvas_api_helper_sections.delete_cache(canvas_course_id)

    logger.debug(
        'Now removing user with user_id=%s from course_instance_id=%s in '
        'CourseManager DB.',
        sis_user_id, course_instance_id
    )

    # find the enrollment in question
    model_class = get_course_member_class(user_role)
    try:
        enrollment = model_class.objects.get(
                         course_instance_id=course_instance_id,
                         user_id=sis_user_id)
    except model_class.DoesNotExist:
        logger.exception('Unable to remove user %s from %s membership in '
                         'course %s: no such membership exists.', sis_user_id,
                         model_class._meta.db_table, course_instance_id)
        return JsonResponse(
            {'result': 'failure',
             'message': 'Error: There was a problem in deleting the user'},
            status=500)

    # now delete it
    try:
        enrollment.delete()
    except Exception as e:
        logger.exception(
            "Error in deleting user=%s from course_instance_id=%s: %s",
            sis_user_id, course_instance_id, e
        )
        return JsonResponse(
            {'result': 'failure',
             'message': 'Error: There was a problem in deleting the user'},
            status=500)

    # Record the delete in the audit log
    audit_logger.info(
        'Course Enrollee=%s was deleted by user=%s for canvas_course_id=%s',
        sis_user_id, request.user.username, canvas_course_id)

    response_data = {
        'result': 'success',
        'message': 'User successfully removed from course',
    }
    return JsonResponse(response_data)


def get_badge_label_name(role_type_cd):
    return settings.MANAGE_PEOPLE['BADGE_LABELS'][get_role_type(role_type_cd)]


def get_role_type(role_type_cd):
    if role_type_cd in ('STUDENT', 'EMPLOYEE', 'CLASPART'):
        return 'huid'
    elif role_type_cd == 'XIDHOLDER':
        return 'xid'
    elif role_type_cd in ('WIDENER', 'COUNTWAY'):
        return 'library'
    else:
        return 'other'


def lti_key_error_response(request, key_error_exception):
    logger.error('Exception: KeyError: %s' % key_error_exception.message)
    user_error_message = settings.MANAGE_PEOPLE['MSGS']['lti_request']
    return render(request, 'manage_people/error.html',
                  context={'message': user_error_message}, status=400)


def _get_people_in_list_query(user_id_list=[]):
    pat = re.compile(r'[^\w]+', re.UNICODE)
    clean_user_ids = ["'{}'".format(pat.sub('', i)) for i in user_id_list if len(pat.sub('', i)) == 8]
    if clean_user_ids:
        # split clean_user_ids into chunks of 999 (https://www.geeksforgeeks.org/break-list-chunks-size-n-python/)
        n = 999
        chunks = [clean_user_ids[i * n:(i + 1) * n] for i in range((len(clean_user_ids) + n - 1) // n)]

        # create the raw query with one of the chunks
        raw_person_query = 'select * from people.v_huid_and_xid_people where univ_id in ({})'.format(','.join(chunks.pop()))
        # if there are remaining chunks, add them to the where clause
        for chunk in chunks:
            raw_person_query += ' or univ_id in ({})'.format(','.join(chunk))
        logger.debug(raw_person_query)
        return raw_person_query
