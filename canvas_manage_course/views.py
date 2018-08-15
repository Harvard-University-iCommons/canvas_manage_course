# -*- coding: utf-8 -*-

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ims_lti_py.tool_config import ToolConfig

from isites_migration.utils import get_previous_isites
from lti_school_permissions.decorators import (
    lti_permission_required,
    lti_permission_required_check)

logger = logging.getLogger(__name__)


@require_http_methods(['GET'])
def tool_config(request):

    url = "https://{}{}".format(request.get_host(), reverse('lti_launch'))

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
@lti_permission_required('canvas_manage_course')
def lti_launch(request):
    return redirect('dashboard_course')


@login_required
@lti_permission_required('canvas_manage_course')
def dashboard_course(request):
    course_instance_id = request.LTI.get('lis_course_offering_sourcedid')

    tool_access_permission_names = [
        'class_roster',
        'im_import_files',  # isites_migration
        'manage_people',
        'manage_sections',
        'custom_fas_card_1']

    # Verify current user permissions to see the apps on the dashboard
    allowed = {tool: lti_permission_required_check(request, tool)
               for tool in tool_access_permission_names}
    no_tools_allowed = not any(allowed.values())

    view_context = {
        'allowed': allowed,
        'no_tools_allowed': no_tools_allowed}

    if no_tools_allowed:
        view_context['custom_error_title'] = u'Not available'
        view_context['custom_error_message'] = \
            u"You do not currently have access to any of the tools available " \
            u"in this view. If you think you should have access, please " \
            u"use \"Help\" to contact Canvas support from Harvard."

    # Check to see if we have any iSites that are available for migration to
    # this Canvas course
    icm_active = len(get_previous_isites(course_instance_id)) > 0
    view_context['isites_migration_active'] = icm_active

    return render(request, 'canvas_manage_course/dashboard_course.html',
                  view_context)
