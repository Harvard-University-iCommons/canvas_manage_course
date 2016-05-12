import logging

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ims_lti_py.tool_config import ToolConfig

from isites_migration.utils import get_previous_isites


logger = logging.getLogger(__name__)


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
def lti_launch(request):
    return redirect('dashboard_course')


@login_required
def dashboard_course(request):
    course_instance_id = request.LTI.get('lis_course_offering_sourcedid')
    # Check to see if we have any iSites that are available for migration to
    # this Canvas course
    icm_active = len(get_previous_isites(course_instance_id)) > 0
    return render(request, 'canvas_course_admin_tools/dashboard_course.html', {
        'icm_active': icm_active
    })
