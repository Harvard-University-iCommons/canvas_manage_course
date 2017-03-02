"""
Django settings for project.

Generated by 'django-admin startproject' using Django 1.8.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import logging
import os
import warnings

from django.core.urlresolvers import reverse_lazy

from .secure import SECURE_SETTINGS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = SECURE_SETTINGS.get('django_secret_key', 'changeme')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = SECURE_SETTINGS.get('enable_debug', False)

# Application definition

INSTALLED_APPS = (
    'async',
    'canvas_manage_course',
    'class_roster',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_auth_lti',
    'django_rq',
    'icommons_common',
    'icommons_common.monitor',
    'icommons_ui',
    'isites_migration',
    # deprecated, but still needed for release v1.5 around for initial migration
    # that translates lti_permissions into lti_school_permissions. See
    # deprecation warning below, and remove when no longer required.
    'lti_permissions',
    'lti_school_permissions',
    'manage_people',
    'manage_sections',
)

# todo: remove lti_permissions from INSTALLED_APPS when no longer needed
warnings.warn("lti_permissions is deprecated. Once lti_school_permissions "
              "migrations have been run to translate existing LtiPermissions "
              "into SchoolPermissions the lti_permission entry can be removed "
              "from INSTALLED_APPS.", DeprecationWarning)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'cached_auth.Middleware',
    'django_auth_lti.middleware_patched.MultiLTILaunchAuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'django_auth_lti.backends.LTIAuthBackend',
)

LOGIN_URL = reverse_lazy('lti_auth_error')

ROOT_URLCONF = 'canvas_manage_course.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': DEBUG,
        },
    },
]

WSGI_APPLICATION = 'canvas_manage_course.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASE_APPS_MAPPING = {
    'async': 'default',
    'auth': 'default',
    'contenttypes': 'default',
    'icommons_common': 'termtool',
    'lti_permissions': 'default',  # deprecated, but still around for migrations
    'lti_school_permissions': 'default',
    'manage_people': 'default',
    'manage_sections': 'default',
}

DATABASE_MIGRATION_WHITELIST = ['default']

DATABASE_ROUTERS = ['icommons_common.routers.DatabaseAppsRouter', ]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': SECURE_SETTINGS.get('db_default_name', 'canvas_manage_course'),
        'USER': SECURE_SETTINGS.get('db_default_user', 'postgres'),
        'PASSWORD': SECURE_SETTINGS.get('db_default_password'),
        'HOST': SECURE_SETTINGS.get('db_default_host', '127.0.0.1'),
        'PORT': SECURE_SETTINGS.get('db_default_port', 5432),  # Default postgres port
    },
    'termtool': {
        'ENGINE': 'django.db.backends.oracle',
        'NAME': SECURE_SETTINGS.get('db_termtool_name'),
        'USER': SECURE_SETTINGS.get('db_termtool_user'),
        'PASSWORD': SECURE_SETTINGS.get('db_termtool_password'),
        'HOST': SECURE_SETTINGS.get('db_termtool_host'),
        'PORT': str(SECURE_SETTINGS.get('db_termtool_port')),
        'OPTIONS': {
            'threaded': True,
        },
        'CONN_MAX_AGE': 0,
    }
}

# Cache
# https://docs.djangoproject.com/en/1.8/ref/settings/#std:setting-CACHES

REDIS_HOST = SECURE_SETTINGS.get('redis_host', '127.0.0.1')
REDIS_PORT = SECURE_SETTINGS.get('redis_port', 6379)

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': "redis://%s:%s/0" % (REDIS_HOST, REDIS_PORT),
        'OPTIONS': {
            'PARSER_CLASS': 'redis.connection.HiredisParser'
        },
        'KEY_PREFIX': 'canvas_manage_course',  # Provide a unique value for intra-app cache
        # See following for default timeout (5 minutes as of 1.7):
        # https://docs.djangoproject.com/en/1.8/ref/settings/#std:setting-CACHES-TIMEOUT
        'TIMEOUT': SECURE_SETTINGS.get('default_cache_timeout_secs', 300),
    },
    'shared': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': "redis://%s:%s/0" % (REDIS_HOST, REDIS_PORT),
        'OPTIONS': {
            'PARSER_CLASS': 'redis.connection.HiredisParser'
        },
        'KEY_PREFIX': 'tlt_shared',
        'TIMEOUT': SECURE_SETTINGS.get('default_cache_timeout_secs', 300),
    }
}

# RQ
# http://python-rq.org/docs/

RQ_QUEUES = {
    'default': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': 0,
    },
    'isites_file_migration': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': 0,
        'DEFAULT_TIMEOUT': SECURE_SETTINGS.get('default_isites_migration_rq_timeout_secs', 180),
    }
}

# Sessions

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# NOTE: This setting only affects the session cookie, not the expiration of the session
# being stored in the cache.  The session keys will expire according to the value of
# SESSION_COOKIE_AGE, which defaults to 2 weeks when no value is given.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'
# A boolean that specifies whether Django's translation system should be enabled. This provides
# an easy way to turn it off, for performance. If this is set to False, Django will make some
# optimizations so as not to load the translation machinery.
USE_I18N = False

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.normpath(os.path.join(BASE_DIR, 'http_static'))

# Logging

_DEFAULT_LOG_LEVEL = SECURE_SETTINGS.get('log_level', logging.DEBUG)
_LOG_ROOT = SECURE_SETTINGS.get('log_root', '')  # Default to current directory

# Turn off default Django logging
# https://docs.djangoproject.com/en/1.8/topics/logging/#disabling-logging-configuration
LOGGING_CONFIG = None

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s\t%(asctime)s.%(msecs)03dZ\t%(name)s:%(lineno)s\t%(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s\t%(name)s:%(lineno)s\t%(message)s',
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    # This is the default logger for any apps or libraries that use the logger
    # package, but are not represented in the `loggers` dict below.  A level
    # must be set and handlers defined.  Setting this logger is equivalent to
    # setting and empty string logger in the loggers dict below, but the separation
    # here is a bit more explicit.  See link for more details:
    # https://docs.python.org/2.7/library/logging.config.html#dictionary-schema-details
    'root': {
        'level': logging.WARNING,
        'handlers': ['default'],
    },
    'handlers': {
        # Log to a file by default that can be rotated by logrotate
        'default': {
            'class': 'logging.handlers.WatchedFileHandler',
            'level': _DEFAULT_LOG_LEVEL,
            'formatter': 'verbose',
            'filename': os.path.join(_LOG_ROOT, 'django-canvas_manage_course.log'),
        },
        'console': {
            'class': 'logging.StreamHandler',
            'level': _DEFAULT_LOG_LEVEL,
            'formatter': 'simple',
            'filters': ['require_debug_true'],
        },
    },
    'loggers': {
        'rq.worker': {
            'handlers': ['default', 'console'],
            'level': _DEFAULT_LOG_LEVEL,
            'propagate': False,
        },
        'icommons_common.async': {
            'handlers': ['default', 'console'],
            'level': _DEFAULT_LOG_LEVEL,
            'propagate': False,
        },
        'isites_migration': {
            'handlers': ['default', 'console'],
            'level': _DEFAULT_LOG_LEVEL,
            'propagate': False,
        },
        'manage_people': {
            'handlers': ['default'],
            'level': _DEFAULT_LOG_LEVEL,
            'propagate': False,
        },
        'manage_people_audit_log': {
            'handlers': ['default'],
            'level': _DEFAULT_LOG_LEVEL,
            'propagate': False,
        },
    }
}

# Currently deployed environment
ENV_NAME = SECURE_SETTINGS.get('env_name', 'local')

# Other app specific settings

LTI_OAUTH_CREDENTIALS = SECURE_SETTINGS.get('lti_oauth_credentials', None)

CANVAS_URL = SECURE_SETTINGS.get('canvas_url', 'https://canvas.harvard.edu')

CANVAS_SDK_SETTINGS = {
    'auth_token': SECURE_SETTINGS.get('canvas_token', None),
    'base_api_url': CANVAS_URL + '/api',
    'max_retries': 3,
    'per_page': 40,
    'session_inactivity_expiration_time_secs': 50,
}

ICOMMONS_COMMON = {
    'ICOMMONS_API_HOST': SECURE_SETTINGS.get('icommons_api_host', None),
    'ICOMMONS_API_USER': SECURE_SETTINGS.get('icommons_api_user', None),
    'ICOMMONS_API_PASS': SECURE_SETTINGS.get('icommons_api_pass', None),
    'CANVAS_API_BASE_URL': CANVAS_URL + '/api/v1',
    'CANVAS_API_HEADERS': {
        'Authorization': 'Bearer ' + SECURE_SETTINGS.get('canvas_token', 'canvas_token_missing_from_config')
    },
    'CANVAS_ROOT_ACCOUNT_ID': SECURE_SETTINGS.get('canvas_root_account_id', 1),
}

# LTI_SCHOOL_PERMISSIONS_TOOL_PERMISSIONS is used by the lti-school-permissions
# app to specify which SchoolPermission.permission names are used in this
# project. Every permission used by an LTI permission check in this project
# should be represented here; e.g. they are used for migrations (to set up
# initial permissions for tool access) and as the list of apps to show in the
# manage permissions UI.
LTI_SCHOOL_PERMISSIONS_TOOL_PERMISSIONS = (
    'canvas_manage_course',  # dashboard
    'class_roster',
    'im_import_files',  # isites_migration app
    'manage_people',
    'manage_sections'
)

MANAGE_PEOPLE = {
    'BADGE_LABELS': {
        'huid': 'HUID',
        'xid': 'XID',
        'library': 'LIBRARY',
        'other': 'OTHER',
    },
    'MSGS': {
        'lti_request': 'There was a problem fulfilling your request. Please contact HUIT support.',
        'no_dir_member_chosen': 'You must choose at least one directory record.',
        'no_role_selected': 'You must choose a role for each user you select.',
        'no_user_selected': 'You must select a user for each role you choose.',
        'success': 'Successful !!!',
    }
}

MANAGE_SECTIONS = {
    'TEST_STUDENT_ROLE': 'StudentViewEnrollment'
}

ICOMMONS_REST_API_TOKEN = SECURE_SETTINGS.get('icommons_rest_api_token')
ICOMMONS_REST_API_HOST = SECURE_SETTINGS.get('icommons_rest_api_host')

# Allows the REST API passthrough to successfully negotiate an SSL session
# with an unverified certificate, e.g. the one that ships with django-sslserver
# Default to False, but if testing locally, set to True
ICOMMONS_REST_API_SKIP_CERT_VERIFICATION = SECURE_SETTINGS.get(
    'icommons_rest_api_skip_cert_verification', False)

ISITES_MIGRATION = {
    'aws_access_key_id': SECURE_SETTINGS.get('isites_migration_aws_access_key_id'),
    'aws_secret_access_key': SECURE_SETTINGS.get('isites_migration_aws_secret_access_key'),
}
