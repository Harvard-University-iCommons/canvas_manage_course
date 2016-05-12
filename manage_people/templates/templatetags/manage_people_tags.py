import re

from django import template
from django.core.cache import cache

from icommons_common.models import UserRole

from manage_people.models import ManagePeopleRole


CACHE_KEY_MANAGE_PEOPLE_TAGS_DISPLAY_NAMES = 'manage-people-tags-display-names'
STRIP_TRAILING_ENROLLMENT_RE = re.compile('Enrollment$')
register = template.Library()


@register.filter(is_safe=True)
def get_role_display_name(role):
    """
    Given a Canvas role name, return our display name for that role. For example
    if we get a role of TaEnrollment, we should return TA.
    :param UserRole:
    :return string:
    """
    display_names = cache.get(CACHE_KEY_MANAGE_PEOPLE_TAGS_DISPLAY_NAMES)
    if display_names is None:
        display_names = load_display_names()
        cache.set(CACHE_KEY_MANAGE_PEOPLE_TAGS_DISPLAY_NAMES, display_names)

    try:
        return 'TA' if 'Teaching Fellow' in display_names[role] else display_names[role]
    except KeyError:
        return STRIP_TRAILING_ENROLLMENT_RE.sub('', role)


@register.filter(is_safe=True)
def tf_to_ta_filter(role):
    return 'TA' if 'Teaching Fellow' in role else role


def load_display_names():
    """
    Load in a mapping from Canvas' role labels to our user role names.
    """
    mp_roles = ManagePeopleRole.objects.all()
    user_roles = UserRole.objects.in_bulk([m.user_role_id for m in mp_roles])

    display_names = {}
    for mp_role in mp_roles:
        display_names[mp_role.canvas_role_label] = \
            user_roles[mp_role.user_role_id].role_name
    return display_names
