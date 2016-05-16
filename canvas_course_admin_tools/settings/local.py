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

dictConfig(LOGGING)

SELENIUM_CONFIG = {
    'canvas_base_url': SECURE_SETTINGS.get('canvas_url'),
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
    'manage_people': {
        'test_course': {
            'cid': '327828',  # courses/27  (see url config below)
        },
        'test_users': {
            '1': {
                'user_id': '01204905',
                'role_id': '10',
            },
            'fake': {
                'user_id': '12345678'
            }
        },
        # Note: for manage_people tests to work as expected the
        # ICOMMONS_REST_API_HOST environment needs to match the LTI tool
        # environment (because of shared cache interactions)
        # 'url': '/courses/27/external_tools/109',  # local cap tool
        'url': '/courses/27/external_tools/72',  # dev cap tool
        # 'url': '/courses/27/external_tools/38',  # qa cap tool
    },
    'run_locally': SECURE_SETTINGS.get('selenium_run_locally', False),
    'selenium_grid_url': SECURE_SETTINGS.get('selenium_grid_url'),
    'selenium_password': SECURE_SETTINGS.get('selenium_password'),
    'selenium_username': SECURE_SETTINGS.get('selenium_user'),
    'use_htmlrunner': SECURE_SETTINGS.get('selenium_use_htmlrunner', True),
}
