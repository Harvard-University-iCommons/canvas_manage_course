from django.urls import path, re_path, include
from django.conf import settings

from canvas_manage_course import views
from icommons_ui import views as icommons_ui_views

urlpatterns = [
    url(r'^course_dashboard$', views.dashboard_course, name='dashboard_course'),
    url(r'^class_roster/', include('class_roster.urls', namespace='class_roster')),
    url(r'^isites_migration/', include('isites_migration.urls', namespace='isites_migration')),
    url(r'^lti_auth_error$', icommons_ui_views.not_authorized, name='lti_auth_error'),
    url(r'^lti_launch$', views.lti_launch, name='lti_launch'),
    url(r'^manage_people/', include('manage_people.urls', namespace='manage_people')),
    url(r'^manage_school_permissions/', include('lti_school_permissions.urls', namespace='manage_school_permissions')),
    url(r'^manage_sections/', include('manage_sections.urls', namespace='manage_sections')),
    url(r'^not_authorized$', icommons_ui_views.not_authorized, name='not_authorized'),
    url(r'^tool_config$', views.tool_config, name='tool_config'),
]

# Import the debug toolbar and handle any namespace issues that may occur
# ie: 'djdt' is not a registered namespace
# https://github.com/jazzband/django-debug-toolbar/issues/529
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ]
    except:
        pass

