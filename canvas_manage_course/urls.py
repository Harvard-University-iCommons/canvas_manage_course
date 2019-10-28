from django.urls import path, re_path, include
from django.conf import settings

from canvas_manage_course import views
from icommons_ui import views as icommons_ui_views

urlpatterns = [

    path('course_dashboard', views.dashboard_course, name='dashboard_course'),
    path('class_roster/', include(('class_roster.urls','class_roster'), namespace='class_roster')),
    path('isites_migration/', include(('isites_migration.urls','isites_migration'), namespace='isites_migration')),
    path('lti_auth_error', icommons_ui_views.not_authorized, name='lti_auth_error'),
    path('lti_launch', views.lti_launch, name='lti_launch'),

    path('manage_people/', include(('manage_people.urls','manage_people'), namespace='manage_people')),
    path('manage_school_permissions/', include(('lti_school_permissions.urls','manage_school_permissions'),
                                               namespace='manage_school_permissions')),
    path('manage_sections/', include(('manage_sections.urls','manage_sections'), namespace='manage_sections')),
    path('not_authorized', icommons_ui_views.not_authorized, name='not_authorized'),
    path('tool_config', views.tool_config, name='tool_config'),
]

# Import the debug toolbar and handle any namespace issues that may occur
# ie: 'djdt' is not a registered namespace
# https://github.com/jazzband/django-debug-toolbar/issues/529
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [
            re_path(r'^__debug__/', include(debug_toolbar.urls)),
        ]
    except:
        pass

