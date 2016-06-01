import re
import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe

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


IS_XID_RE = re.compile('[a-z]', re.IGNORECASE)
SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)
logger = logging.getLogger(__name__)


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

    try:
        course_instance = CourseInstance.objects.get(
                              course_instance_id=course_instance_id)
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
        default_roles = ManagePeopleRole.objects.values_list(
                            'user_role_id', 'xid_allowed')
        xid_allowed_by_role_id = dict(default_roles)

    # now get the role details, add in xid_allowed
    user_role_query = UserRole.objects.filter(
                           role_id__in=xid_allowed_by_role_id.keys())
    user_roles = user_role_query.order_by('role_name').values()
    available = []
    for role in user_roles:
        role['xid_allowed'] = xid_allowed_by_role_id[role['role_id']]
        available.append(role)
    return available


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
