import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ims_lti_py.tool_config import ToolConfig

from django_auth_lti import const
from django_auth_lti.decorators import lti_role_required
from django_auth_lti.verification import is_allowed
from isites_migration.utils import get_previous_isites
from lti_permissions.decorators import lti_permission_required_check
from manage_sections.views import (
    LTI_ROLES_PERMITTED as manage_sections_lti_roles_permitted,)

logger = logging.getLogger(__name__)

LTI_ROLES_PERMITTED = [
    const.ADMINISTRATOR,
    const.CONTENT_DEVELOPER,
    const.INSTRUCTOR,
    const.TEACHING_ASSISTANT,
]


@require_http_methods(['GET'])
def tool_config(request):
    url = "%s://%s%s" % (request.scheme, request.get_host(),
                         reverse('lti_launch', exclude_resource_link_id=True))
    title = 'Manage Course'
    lti_tool_config = ToolConfig(
        title=title,
        launch_url=url,
        secure_launch_url=url,
        description="This LTI tool provides a suite of tools for administering your Canvas course."
    )

    # this is how to tell Canvas that this tool provides a course navigation link:
    nav_params = {
        'enabled': 'true',
        'text': title,
        'default': 'disabled',
        'visibility': 'admins',
    }
    custom_fields = {'canvas_membership_roles': '$Canvas.membership.roles'}
    lti_tool_config.set_ext_param('canvas.instructure.com', 'custom_fields', custom_fields)
    lti_tool_config.set_ext_param('canvas.instructure.com', 'course_navigation', nav_params)
    lti_tool_config.set_ext_param('canvas.instructure.com', 'privacy_level', 'public')

    return HttpResponse(lti_tool_config.to_xml(), content_type='text/xml')


@login_required
@require_http_methods(['POST'])
@csrf_exempt
@lti_role_required(LTI_ROLES_PERMITTED)
def lti_launch(request):
    return redirect('dashboard_course')


@login_required
@lti_role_required(LTI_ROLES_PERMITTED)
def dashboard_course(request):
    course_instance_id = request.LTI.get('lis_course_offering_sourcedid')

    # list of permissions to determine tool visibility
    tools = {
        'isites_migration': {
            'visible': lti_permission_required_check(request, settings.CUSTOM_LTI_PERMISSIONS['isites_migration'])},
        'manage_people': {
            'visible': lti_permission_required_check(request, settings.CUSTOM_LTI_PERMISSIONS['manage_people'])},
        'manage_sections': {
            'visible': _lti_role_allowed(request, manage_sections_lti_roles_permitted)},
    }

    # django template tags can't do dict lookups, so create a *_visible context
    # variable for each tool
    tool_visibility = {
        '{}_visible'.format(tool): tools[tool]['visible']
        for tool in tools.keys()}

    view_context = tool_visibility

    # are all tools hidden?
    no_tools_visible = len(filter(lambda x: x, tool_visibility.values())) == 0
    view_context['no_tools_visible'] = no_tools_visible

    # Check to see if we have any iSites that are available for migration to
    # this Canvas course
    icm_active = len(get_previous_isites(course_instance_id)) > 0
    view_context['isites_migration_active'] = icm_active

    return render(request, 'canvas_course_admin_tools/dashboard_course.html',
                  view_context)


def _lti_role_allowed(request, lti_roles_permitted, raise_exception=False):
    """ utility method to convert is_allowed() to a boolean """
    user_allowed_roles = is_allowed(request, lti_roles_permitted,
                                    raise_exception)
    return len(user_allowed_roles) > 0
