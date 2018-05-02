from __future__ import unicode_literals
import itertools

from django.db import migrations

from lti_school_permissions import settings as lti_perm_settings

# Adds new roles to the lti_school_permissions table and removes all isites migration permission records.

PERMISSION_NAMES = ['canvas_manage_course',
                    'class_roster',
                    'manage_people',
                    'manage_sections']

NEW_ROLES = [
    'Head Instructor',
    'Instructor',
    'Primary Instructor',
    'Secondary Instructor',
    'Course Director',
    'TF/TA Instructor',
    'Faculty Assistant',
    'Preceptor'
]


def _get_permissions():
    return itertools.product(
        PERMISSION_NAMES,
        lti_perm_settings.SCHOOLS,  # should be all schools
        NEW_ROLES)


def create_school_permissions(school_permission_class):
    fields = ('permission', 'school_id', 'canvas_role')

    for permission in _get_permissions():
        school_permission_class.objects.create(**dict(zip(fields, permission)))


def update_school_permissions(apps, schema_editor):
    school_permission_class = apps.get_model('lti_school_permissions',
                                             'SchoolPermission')

    create_school_permissions(school_permission_class)

    # Remove isites migrations records
    school_permission_class.objects.filter(permission='im_import_files').delete()


def reverse_permissions_load(apps, schema_editor):
    school_permission_class = apps.get_model('lti_school_permissions',
                                             'SchoolPermission')
    school_permission_class.objects.filter(
        canvas_role__in=NEW_ROLES,
        permission__in=PERMISSION_NAMES,
        school_id__in=lti_perm_settings.SCHOOLS,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('canvas_manage_course', '0001_initial_dashboard_schoolpermissions'),
    ]

    operations = [
        migrations.RunPython(
            code=update_school_permissions,
            reverse_code=reverse_permissions_load,
        ),
    ]
