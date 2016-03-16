from django.conf.urls import include, url

from icommons_ui import views as icommons_ui_views

from canvas_course_admin_tools import views


urlpatterns = [
    url(r'^lti_auth_error$', icommons_ui_views.not_authorized, name='lti_auth_error'),
    url(r'^not_authorized$', icommons_ui_views.not_authorized, name='not_authorized'),
    url(r'^tool_config$', views.tool_config, name='tool_config'),
    url(r'^lti_launch$', views.lti_launch, name='lti_launch'),
    url(r'^course_dashboard$', views.dashboard_course, name='dashboard_course'),
    url(r'^isites_migration/', include('isites_migration.urls', namespace='isites_migration')),
]