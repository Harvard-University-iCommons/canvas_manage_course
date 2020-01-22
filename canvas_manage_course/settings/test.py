from .local import *

DATABASE_APPS_MAPPING = {
    'auth': 'default',
    'contenttypes': 'default',
    'icommons_common': 'default',
    'lti_permissions': 'default',  # deprecated, but still around for migrations
    'lti_school_permissions': 'default',
    'manage_people': 'default',
    'manage_sections': 'default',
    'sessions': 'default',
}

DATABASE_MIGRATION_WHITELIST = ['default']

# Make tests faster by using sqlite3
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    },
    'shared': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    }
}

"""
Unit tests should be able to run without talking to external services like
redis/elasticache.  Let's disable the caching middleware, and use the db
to store session data.
"""
MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE[MIDDLEWARE.index('cached_auth.Middleware')] = \
    'django.contrib.auth.middleware.AuthenticationMiddleware'
MIDDLEWARE = tuple(MIDDLEWARE)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

"""
Don't assume we'll have oauth credentials set for us in secure.py, set
them up here instead.
"""
SECURE_SETTINGS.setdefault('lti_oauth_credentials', {}).update({'foo': 'bar'})
if not LTI_OAUTH_CREDENTIALS:
    LTI_OAUTH_CREDENTIALS = {}
LTI_OAUTH_CREDENTIALS.update({'foo': 'bar'})
SECURE_SETTINGS.setdefault('canvas_token', 'foo')
if not CANVAS_SDK_SETTINGS:
    CANVAS_SDK_SETTINGS = {}
CANVAS_SDK_SETTINGS.update({'auth_token': 'foo'})
