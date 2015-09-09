from django.conf.urls import include, url

from canvas_admin_tools import views


urlpatterns = [
    url(r'^lti_auth_error/', views.lti_auth_error, name='lti_auth_error'),
    url(r'^tool_config_account$', views.tool_config_account, name='tool_config_account'),
    url(r'^tool_config_course$', views.tool_config_course, name='tool_config_course'),
    url(r'^lti_launch$', views.lti_launch, name='lti_launch'),
    url(r'^account_dashboard$', views.dashboard_account, name='dashboard_account'),
    url(r'^course_dashboard$', views.dashboard_course, name='dashboard_course'),
]
