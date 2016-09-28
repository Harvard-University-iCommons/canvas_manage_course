# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps as real_apps
from django.db import migrations

LTI_PERMISSIONS_DATA = [
    ('manage_sections', '*', 'AccountAdmin', True),
    ('manage_sections', '*', 'Account Admin', True),
    ('manage_sections', '*', 'Account Observer', True),
    ('manage_sections', '*', 'Course Head', True),
    ('manage_sections', '*', 'Course Support Staff', True),
    ('manage_sections', '*', 'Department Admin', True),
    ('manage_sections', '*', 'DesignerEnrollment', True),
    ('manage_sections', '*', 'Faculty', True),
    ('manage_sections', '*', 'Guest', False),
    ('manage_sections', '*', 'Harvard-Viewer', False),
    ('manage_sections', '*', 'Help Desk', True),
    ('manage_sections', '*', 'Librarian', True),
    ('manage_sections', '*', 'ObserverEnrollment', False),
    ('manage_sections', '*', 'SchoolLiaison', True),
    ('manage_sections', '*', 'Prospective Enrollee', False),
    ('manage_sections', '*', 'StudentEnrollment', False),
    ('manage_sections', '*', 'TaEnrollment', True),
    ('manage_sections', '*', 'TeacherEnrollment', True),
    ('manage_sections', '*', 'Teaching Staff', True),
    ('manage_sections', 'colgsas', 'Account Observer', False),
    ('manage_sections', 'colgsas', 'DesignerEnrollment', False),
    ('manage_sections', 'colgsas', 'Librarian', False),
    ('manage_sections', 'ext', 'Account Observer', False),
    ('manage_sections', 'ext', 'Librarian', False),
    ('manage_sections', 'gse', 'Help Desk', False),
    ('manage_sections', 'hilr', 'Account Observer', False),
    ('manage_sections', 'hilr', 'Librarian', False),
    ('manage_sections', 'hks', 'Course Head', False),
    ('manage_sections', 'hks', 'Course Support Staff', False),
    ('manage_sections', 'hks', 'DesignerEnrollment', False),
    ('manage_sections', 'hks', 'Librarian', False),
    ('manage_sections', 'hks', 'TaEnrollment', False),
    ('manage_sections', 'hks', 'Teaching Staff', False),
    ('manage_sections', 'hls', 'Account Observer', False),
    ('manage_sections', 'hls', 'Course Head', False),
    ('manage_sections', 'hls', 'Course Support Staff', False),
    ('manage_sections', 'hls', 'Department Admin', False),
    ('manage_sections', 'hls', 'DesignerEnrollment', False),
    ('manage_sections', 'hls', 'Faculty', False),
    ('manage_sections', 'hls', 'Help Desk', False),
    ('manage_sections', 'hls', 'Librarian', False),
    ('manage_sections', 'hls', 'TaEnrollment', False),
    ('manage_sections', 'hls', 'TeacherEnrollment', False),
    ('manage_sections', 'hls', 'Teaching Staff', False),
    ('manage_sections', 'sum', 'Account Observer', False),
    ('manage_sections', 'sum', 'Librarian', False)
]


def create_lti_permissions(apps, schema_editor):
    try:
        LtiPermission = apps.get_model('lti_permissions', 'LtiPermission')
    except LookupError:
        # If the LtiPermission table doesn't exist, return from here
        return

    fields = ('permission', 'school_id', 'canvas_role', 'allow')

    for permission in LTI_PERMISSIONS_DATA:
        LtiPermission.objects.create(**dict(zip(fields, permission)))


def reverse_permissions_load(apps, schema_editor):
    try:
        LtiPermission = apps.get_model('lti_permissions', 'LtiPermission')
    except LookupError:
        # If the LtiPermission table doesn't exist, return from here
        return

    LtiPermission.objects.filter(permission='manage_sections').delete()


class Migration(migrations.Migration):

    dependencies = []

    # tlt-2650: we need to check whether lti_permissions is part of
    # INSTALLED_APPS and skip this migration if the LtiPermission model is
    # not available.
    if real_apps.is_installed('lti_permissions'):
        dependencies.append(('lti_permissions', '0001_initial'))

    operations = [
        migrations.RunPython(
            code=create_lti_permissions,
            reverse_code=reverse_permissions_load,
        ),
    ]
