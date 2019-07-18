import json
import logging
import re

from django.conf import settings
from django.core.cache import caches
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe

from icommons_common.canvas_api.helpers.roles import get_roles_for_account_id
from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_common.models import (
    CourseEnrollee,
    CourseGuest,
    CourseInstance,
    CourseStaff,
    UserRole,
)

from manage_people.models import (
    ManagePeopleRole,
    SchoolAllowedRole,
)


cache = caches['shared']
CACHE_KEY_CANVAS_ROLES_BY_USER_ROLE_ID_FOR_ACCOUNT = "canvas-roles-by-user-role-id-for-account-{}"
logger = logging.getLogger(__name__)
IS_XID_RE = re.compile('[a-z]', re.IGNORECASE)
SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)



def context_error(request):
    """
    This method will helps in error handling and is used by the validation
    methods. It return a  HttpResponse if the request is via AJAX otherwise
    renders the error page.
    """
    errormsg = ("Looks like you've been working on multiple Canvas sites. "
                "<br/>Click on <strong>Manage People</strong> in the left "
                "navigation to continue.")
    if request.is_ajax():
        return HttpResponse(mark_safe(errormsg),
                            content_type="application/json",
                            status=424)
    else:
        return render(request, 'manage_people/error.html',
                      {'message': mark_safe(errormsg)})


def get_available_roles(course_instance_id):
    """
    This utility returns the list of UserRoles allowed for the school of the
    provided course_instance_id as defined by the SchoolAllowedRoles for that
    school. If no SchoolAllowedRoles are defined for the school, it defaults to
    the full set of UserRoles that are referenced from ManagePeopleRoles. If
    course_instance_id is missing, an empty dict is returned.
    :return: dict of allowed roles mapped by canvas_role_id
    """
    if not course_instance_id:
        logger.warning(u'get_available_roles called with course_instance_id %s',
                       course_instance_id)
        return {}

    cache_key = 'course_instance_available_roles_{}'.format(
        course_instance_id)
    user_roles_list = cache.get(cache_key)
    if user_roles_list is not None:
        logger.debug('found course_instance_available_roles in cache')
        return user_roles_list
    else:
        logger.debug('available_roles CACHE MISS')

    try:
        course_instance = CourseInstance.objects.select_related('course__school').get(
                course_instance_id=course_instance_id
            )
        school_id = course_instance.course.school.school_id
    except ObjectDoesNotExist:
        logger.exception(u'course instance id %s does not exist',
                         course_instance_id)
        return {}
    except AttributeError:
        logger.exception(u'unable to find school id for course instance %s',
                         course_instance_id)
        return {}
    except RuntimeError as e:
        logger.exception(u'unexpected error %s attempting to find school id '
                         u'for course instance %s', e, course_instance_id)
        return {}

    # if the school defined a set of allowed roles, use only those
    allowed_roles = SchoolAllowedRole.objects.filter(school_id=school_id) \
                        .values_list('user_role_id', 'xid_allowed')
    xid_allowed_by_role_id = dict(allowed_roles)

    # otherwise, use the default set
    if not xid_allowed_by_role_id:
        allowed_roles = ManagePeopleRole.objects.values_list(
                            'user_role_id', 'xid_allowed')
        xid_allowed_by_role_id = dict(allowed_roles)

    allowed_role_ids = [allowed_role[0] for allowed_role in allowed_roles]

    # now get the role details, add in xid_allowed
    user_role_query = UserRole.objects.filter(
                           role_id__in=xid_allowed_by_role_id.keys())
    user_roles = user_role_query.values()

    available = []
    for role in user_roles:
        if role['role_id'] in allowed_role_ids:
            role['xid_allowed'] = xid_allowed_by_role_id[role['role_id']]
            available.append(role)

    # get the updated (or cached) Canvas role list so we can show the right
    # role labels in the available roles dropdown list
    canvas_roles_by_role_id = get_roles_for_account_id('self')
    labels_by_user_role_id = {
        role['role_id']: canvas_roles_by_role_id[
            int(role['canvas_role_id'])]['label']
        for role in user_roles
        if role.get('canvas_role_id')
        and canvas_roles_by_role_id.get(
            int(role['canvas_role_id']), {}).get('label')}

    # annotate available roles with the current Canvas role label
    for role in user_roles:
        role['canvas_role_label'] = labels_by_user_role_id[
            role['role_id']] if labels_by_user_role_id.get(
            role['role_id']) else ''

    user_roles_list = list(user_roles)
    user_roles_list.sort(key=lambda x: x['canvas_role_label'])
    cache.set(cache_key, user_roles_list, 3600)
    return user_roles_list


def get_course_member_class(user_role):
    """
    Returns the model class for the correct course membership table (currently
    COURSE_ENROLLEE, COURSE_STAFF, or COURSE_GUEST) for this role.

    NOTE: The db puts no constraints on multiple is_* columns being set to 1,
    so we assume STAFF trumps ENROLLEE trumps GUEST.
    """
    if int(user_role.staff):
        return CourseStaff
    elif int(user_role.student):
        return CourseEnrollee
    elif int(user_role.guest):
        return CourseGuest
    else:
        raise RuntimeError(u'User role %s is neither staff, nor student, nor '
                           u'guest.  Unable to determine which table to use.',
                           user_role)


def is_xid(id):
    """
    check if the id is an XID. XID's are always alphanumeric while
    non XID's are all numeric.
    :param id: the id to check
    :return boolean:
    """
    match = IS_XID_RE.match(id)
    return match is not None


def get_user_role_if_permitted(course_instance_id, user_role_id):
    """
    Checks to see if user_role_id is a valid UserRole and is permitted by the
    SchoolAllowedRole rules (or ManagePeopleRole defaults)
    :return: a UserRole object, if permitted, or None if role is not permitted
    """
    user_role = None

    available_roles = get_available_roles(course_instance_id)

    if int(user_role_id) in [int(role['role_id']) for role in available_roles]:
        try:
            user_role = UserRole.objects.get(role_id=user_role_id)
        except UserRole.DoesNotExist:
            logger.exception(
                u'user_role_id %s does not map to a valid user_role record.',
                user_role_id)
    else:
        logger.exception(
            u'user_role_id %s does not map to a permitted user_role record for '
            u'course %s. Permitted roles: %s', user_role_id, course_instance_id,
            sorted([role['role_id'] for role in available_roles]))

    return user_role


def get_canvas_role_name(user_role_id):
    """
    Provides the Canvas role name (the 'role' value of a role object as defined
    in the Canvas API) for a user role.
    """
    # get the updated (or cached) Canvas role list so code that still uses the
    # role name for enrollments will have up-to-date role names
    role_map = get_user_role_to_canvas_role_map()
    return role_map[user_role_id]['role']


def get_user_role_to_canvas_role_map(account_id='self'):
    """
    Builds a map of UserRole.role_ids to their corresponding Canvas role objects
    (via UserRole.canvas_role_id).
    :param account_id: Canvas account ID to fetch Canvas role list for. Defaults
    to self because for the time being roles are only defined at the root
    account in Canvas.
    """
    cache_key = CACHE_KEY_CANVAS_ROLES_BY_USER_ROLE_ID_FOR_ACCOUNT.format(
        account_id)
    role_map = cache.get(cache_key)
    if role_map is not None:
        return role_map

    canvas_roles_by_canvas_role_id = get_roles_for_account_id(account_id)
    user_roles = UserRole.objects.values()
    role_map = {
        role['role_id']: canvas_roles_by_canvas_role_id[role['canvas_role_id']]
        for role in user_roles if role.get('canvas_role_id')}

    logger.debug(
        u"Caching user_role_id:Canvas role map for Canvas account %s: %s",
        account_id, json.dumps(str(role_map)).replace("'", '"'))
    cache.set(cache_key, role_map)
    return role_map


def get_canvas_to_user_role_id_map():
    """
    Builds a map (dict) of UserRole.canvas_role_ids to UserRole.role_ids.
    """

    # todo: this will not accurately work for any roles that have many:one maps
    # (such as the Canvas student role) - see TLT-2766 (raise a ticket)
    return {int(canvas_role_id): int(user_role_id)
            for canvas_role_id, user_role_id
            in UserRole.objects.filter(canvas_role_id__isnull=False)\
                .values_list('canvas_role_id', 'role_id')}
