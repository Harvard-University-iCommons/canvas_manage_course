# -*- coding: utf-8 -*-

import logging
import urllib.request, urllib.parse, urllib.error
import urllib.parse

from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from lti.tool_config import ToolConfig
from lti_school_permissions.decorators import (
    lti_permission_required,
    lti_permission_required_check)

logger = logging.getLogger(__name__)


@require_http_methods(['GET'])
def tool_config(request):

    url = "https://{}{}".format(request.get_host(), reverse('lti_launch'))
    url = _url(url)

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


def _url(url):
    """
    *** Taken from ATG's django-app-lti repo to fix the issue of resource_link_id being included in the launch url
    *** TLT-3591
    Returns the URL with the resource_link_id parameter removed from the URL, which
    may have been automatically added by the reverse() method. The reverse() method is
    patched by django-auth-lti in applications using the MultiLTI middleware. Since
    some applications may not be using the patched version of reverse(), we must parse the
    URL manually and remove the resource_link_id parameter if present. This will
    prevent any issues upon redirect from the launch.
    """
    parts = urllib.parse.urlparse(url)
    query_dict = urllib.parse.parse_qs(parts.query)
    if 'resource_link_id' in query_dict:
        query_dict.pop('resource_link_id', None)
    new_parts = list(parts)
    new_parts[4] = urllib.parse.urlencode(query_dict)
    return urllib.parse.urlunparse(new_parts)


@login_required
@require_http_methods(['POST'])
@csrf_exempt
@lti_permission_required('canvas_manage_course')
def lti_launch(request):
    return redirect('dashboard_course')


@login_required
@lti_permission_required('canvas_manage_course')
def dashboard_course(request):

    tool_access_permission_names = [
        'class_roster',
        'manage_people',
        'manage_sections',
        'custom_fas_card_1']

    # Verify current user permissions to see the apps on the dashboard
    allowed = {tool: True
               for tool in tool_access_permission_names}
    no_tools_allowed = not any(allowed.values())

    view_context = {
        'allowed': allowed,
        'no_tools_allowed': no_tools_allowed}

    if no_tools_allowed:
        view_context['custom_error_title'] = 'Not available'
        view_context['custom_error_message'] = \
            "You do not currently have access to any of the tools available " \
            "in this view. If you think you should have access, please " \
            "use \"Help\" to contact Canvas support from Harvard."

    return render(request, 'canvas_manage_course/dashboard_course.html', view_context)
