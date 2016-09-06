from __future__ import unicode_literals
import itertools

from django.db import migrations

from lti_permissions.models import WHITELISTED_ROLES, DEFAULT_SCHOOLS

# open dashboard to all course and account administration roles not covered in
# lti_permissions.migrations.0003_schoolpermission_default_data
PERMISSION_NAMES = ['canvas_manage_course']
SCHOOL_PERMISSION_DATA = itertools.product(
    PERMISSION_NAMES,
    DEFAULT_SCHOOLS,  # should be all schools
    WHITELISTED_ROLES)  # should not include account admin


def create_school_default_permissions(apps, schema_editor):
    school_permission_class = apps.get_model('lti_permissions',
                                             'SchoolPermission')
    fields = ('permission', 'school_id', 'canvas_role')

    for permission in SCHOOL_PERMISSION_DATA:
        school_permission_class.objects.create(**dict(zip(fields, permission)))


def reverse_permissions_load(apps, schema_editor):
    school_permission_class = apps.get_model('lti_permissions',
                                             'SchoolPermission')
    school_permission_class.objects.filter(
        canvas_role__in=WHITELISTED_ROLES,
        permission__in=PERMISSION_NAMES,
        school_id__in=DEFAULT_SCHOOLS,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('lti_permissions', '0004_schoolpermission_custom_data'),
    ]

    operations = [
        migrations.RunPython(
            code=create_school_default_permissions,
            reverse_code=reverse_permissions_load,
        ),
    ]
