from .local import *

# Make tests faster

DATABASE_ROUTERS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'canvas_admin_tools',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    },
    'shared': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    }
}
