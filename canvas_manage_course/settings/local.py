from .base import *
from logging.config import dictConfig

ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

INSTALLED_APPS += ('debug_toolbar', 'sslserver')
MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)

# For Django Debug Toolbar:
INTERNAL_IPS = ('127.0.0.1', '10.0.2.2',)
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

# Log to console instead of a file when running locally
LOGGING['handlers']['default'] = {
    'level': logging.DEBUG,
    'class': 'logging.StreamHandler',
    'formatter': 'simple',
}

CONCLUDE_COURSES_URL = SECURE_SETTINGS.get(
    'conclude_courses_url',
    'https://icommons-tools.dev.tlt.harvard.edu/course_conclusion'
)

CLASS_ROSTER = {
    'sis_roster': {
        'base_path': SECURE_SETTINGS.get('sis_roster_base_path', 'psp/hrvcsint'),
        'static_path': '/EMPLOYEE/HRMS/c/SA_LEARNING_MANAGEMENT.SS_CLASS_ROSTER.GBL',
        'base_url': SECURE_SETTINGS.get('sis_roster_base_url', 'https://csint.my.harvard.edu/'),
        'base_query': '?Page=CLASS_ROSTER&Action=U&ExactKeys=Y&INSTITUTION=HRVRD&',
    }
}

dictConfig(LOGGING)

SELENIUM_CONFIG = {
    'canvas_base_url': SECURE_SETTINGS.get('canvas_url'),
    'class_roster': {
        'course_link': 'courses/3787/external_tools/162',
        'roster_text_display': 'JAPAN BA 001',
        'url_link_course_number': '14754',
        # See TLT-1767 for how the strm code is constructed.
        'url_strm_term_code': '2151',
    },
    'debug': {
        'log_config': {
            'incremental': True,
            # prevents selenium debug messages when in local/text output mode
            'loggers': {'selenium': {'level': 'ERROR'}},
            'version': 1
        },
        # 'screenshots_on_failure': True,
    },
    'icommons_rest_api': {
        'base_path': 'api/course/v2'
    },
    'manage_course': {
        'relative_url': 'courses/27/external_tools/170',  # dev (Manage Course)
    },
    'manage_people': {
        'test_course': {
            'cid': '327828',  # courses/27  (see url config below)
        },
        'test_users': {
            '1': {
                'user_id': '01819033',
                'role_id': '10',
            },
            'fake': {
                'user_id': '12345678'
            }
        },
    },
    'run_locally': SECURE_SETTINGS.get('selenium_run_locally', False),
    'selenium_grid_url': SECURE_SETTINGS.get('selenium_grid_url'),
    'selenium_password': SECURE_SETTINGS.get('selenium_password'),
    'selenium_username': SECURE_SETTINGS.get('selenium_user'),
    'use_htmlrunner': SECURE_SETTINGS.get('selenium_use_htmlrunner', True),
}
