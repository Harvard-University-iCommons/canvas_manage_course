import functools
import logging
import re
import uuid

from canvas_api.helpers import courses as canvas_api_helper_courses
from canvas_api.helpers import enrollments as canvas_api_helper_enrollments
from canvas_api.helpers import sections as canvas_api_helper_sections
from canvas_sdk.exceptions import CanvasAPIError
from canvas_sdk.methods import enrollments as canvas_api_enrollments
from canvas_sdk.methods import sections
from django.conf import settings
from icommons_common.canvas_api.helpers import \
    courses as canvas_api_helper_courses
from icommons_common.canvas_api.helpers import \
    enrollments as canvas_api_helper_enrollments
from icommons_common.canvas_api.helpers import \
    sections as canvas_api_helper_sections
from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_common.models import CourseInstance

logger = logging.getLogger(__name__)

# Set up the request context that will be used for canvas API calls
SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)


def role_key(enrollment):
    """
    Return a tuple key for an enrollment record based on user_id and role
    """
    return enrollment['user_id'], enrollment['role_id']


def unique_enrollments_not_in_section_filter(section_id, enrollments):
    """
    For a given set of enrollments and section id, return a subset of enrollments
    that are unique in terms of the 'role_key' defined above and whose 'role_key'
    is not already present in the given section.
    """
    section_set = {role_key(x) for x in enrollments if x['course_section_id'] == int(section_id)}
    # Use a temporary dictionary to get unique enrollments based on the "role_key".  Filter out any
    # records where the role_key is present in the current section (by using the section_set above)
    return list({role_key(x): x for x in enrollments if role_key(x) not in section_set}.values())


def get_section_by_id(section_id):
    """
    This method will retreive the section given the section id
    """
    response = sections.get_section_information_sections(SDK_CONTEXT, section_id)
    section = response.json()
    return section


def is_enrollment_section(sis_section_id):
    """
    Check if the sis_section_id belongs to an enrollment section.
    In this case an enrollment section is one where the section_type is 'E'
    :param sis_section_id:
    :return boolean:
    """
    if sis_section_id:
        if sis_section_id.isdigit():
            try:
                return CourseInstance.objects.get(course_instance_id=int(sis_section_id)).is_enrollment_section
            except (CourseInstance.DoesNotExist, CourseInstance.MultipleObjectsReturned, ValueError) as e:
                return False
    return False


def is_sis_section(sis_section_id):
    """
    Check if the sis_section_id exists in the CourseInstance table.
    If it does (and the source isn't 'managecrs') it is an sis section.
    :param sis_section_id:
    :return boolean:
    """
    if sis_section_id:
        if sis_section_id.isdigit():
            try:
                ci = CourseInstance.objects.get(course_instance_id=int(sis_section_id))
                if ci and ci.source != 'managecrs':
                    return True
            except (CourseInstance.DoesNotExist, CourseInstance.MultipleObjectsReturned, ValueError) as e:
                return False
    return False


def is_credit_status_section(sis_section_id):
    """
    This helper method is to check to see if the passed in section is section fed by registrar
    Set to True if it is a registrar section, set to False if it is not
    """
    if sis_section_id:
        # We currently have  Ext and fas fed registrar section with following formats:
        # 1. Extension - 'ext:*', which maps to an extension-school credit-status based section
        # 2. Fas- 'fas:*' for sections created via the FAS Registrar's section tool
        if re.match('^(ext|fas):\w+$', sis_section_id):
            return True
    return False


@functools.singledispatch
def is_editable_section(arg):
    raise NotImplementedError(f'Unsupported type: {type(arg)}')


@is_editable_section.register
def is_editable_section_str(section: str):
    """
    This is a helper method to check if the section is editable. If it's a primary section or a
    registrar section it shouldn't be editable.
    Set to True if it is a primary/registrar section, set to False if it is not
    """
    if not section:
        return False
    if is_sis_section(section) or is_credit_status_section(section):
        return False

    return True


@is_editable_section.register
def is_editable_section_dict(section: dict):
    """
    This is a helper method to check if the section is editable. If it's a primary section or a
    registrar section it shouldn't be editable.
    Set to True if it is a primary/registrar section, set to False if it is not
    """
    sis_section_id = section.get('sis_section_id')
    if not sis_section_id:
        return False
    if is_sis_section(sis_section_id) or is_credit_status_section(sis_section_id):
        return False

    return True


def validate_course_id(section_canvas_course_id, request_canvas_course_id):
    """
    This helper method is to check if  the 2 course id passed in match
    (typically the section's course id and the one from request)
    """
    # check and convert the canvas_id from request to an int
    if not isinstance(request_canvas_course_id, int):
        request_canvas_course_id = int(request_canvas_course_id)

    if section_canvas_course_id == request_canvas_course_id:
        return True
    return False


def delete_enrollments(enrollments, course_id):
    """
    Delete a list of enrollments via Canvas API.
    Clears cache of section, enrollment, and
    course data.

    Returns a tuple `(deleted_enrollments, is_empty)`:
    - `deleted_enrollments` is a list of successful Canvas SDK responses
    - `is_empty` is a boolean indicating to the caller whether the section
    was successfully emptied (or was already empty)
    """
    is_empty = False
    deleted_enrollments = []

    if not enrollments:
        is_empty = True
        return (deleted_enrollments, is_empty)

    for enrollment in enrollments:
        user_section_id = enrollment.get('id', '')
        if not user_section_id:
            logger.error(
                f'Unexpected error while concluding enrollment for '
                f'course_id:{course_id}; no user_section_id available '
                f'for enrollment {enrollment}',
                extra={
                    'deleted_enrollments': deleted_enrollments,
                    'enrollment_causing_error': enrollment,
                    'enrollments_requested': enrollments,
                }
            )
            return (deleted_enrollments, is_empty)
        response = None
        try:
            response = canvas_api_enrollments.conclude_enrollment(
                SDK_CONTEXT, course_id, user_section_id, 'delete'
            )
        except CanvasAPIError as e:
            logger.exception(
                f'Unexpected error while concluding enrollment for '
                f'user_section_id:{user_section_id}, '
                f'course_id:{course_id}',
                extra={'canvas_api_error': getattr(e, 'error_json', None)},
            )
            canvas_api_helper_sections.delete_cache(course_id)
            return (deleted_enrollments, is_empty)

        canvas_api_helper_sections.delete_section_cache(user_section_id)
        deleted_enrollments.append(response)

    is_empty = True

    canvas_api_helper_courses.delete_cache(canvas_course_id=course_id)
    canvas_api_helper_enrollments.delete_cache(course_id)
    canvas_api_helper_sections.delete_cache(course_id)

    return (deleted_enrollments, is_empty)


def create_db_section(course_instance: CourseInstance, section_name: str):
    try:
        db_course_section = CourseInstance(
            cs_class_type='N',
            parent_course_instance_id=course_instance.course_instance_id,
            course_id=course_instance.course_id,
            term=course_instance.term,
            source='managecrs',
            sync_to_canvas = 1,
            title = section_name.strip(),
            short_title = section_name.strip(),
            section = str(uuid.uuid4())
        )
        db_course_section.save()
    except Exception as e:
        logger.exception(
            f'Unexpected error while creating section for '
            f'parent_course_instance_id: {course_instance.course_instance_id}',
            extra={'error': e},
        )
        raise

    logger.info(
        f'Successfully created section for '
        f'parent_course_instance_id: {course_instance.course_instance_id}',
        extra={
            'course_instance_id': db_course_section.course_instance_id,
            'title': db_course_section.title,
        }
    )

    return db_course_section
