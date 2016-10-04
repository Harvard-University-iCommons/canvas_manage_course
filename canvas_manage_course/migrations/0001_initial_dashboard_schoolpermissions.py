from __future__ import unicode_literals
import itertools

from django.db import migrations

from lti_school_permissions import settings as lti_perm_settings

# open dashboard to all course and account administration roles not covered in
# lti_school_permissions.migrations.0003_school_permission_default_data
PERMISSION_NAMES = ['canvas_manage_course']


def _get_permissions():
    return itertools.product(
        PERMISSION_NAMES,
        lti_perm_settings.SCHOOLS,  # should be all schools
        lti_perm_settings.WHITELISTED_ROLES)  # should not include account admin


def create_school_default_permissions(apps, schema_editor):
    school_permission_class = apps.get_model('lti_school_permissions',
                                             'SchoolPermission')
    fields = ('permission', 'school_id', 'canvas_role')

    for permission in _get_permissions():
        school_permission_class.objects.create(**dict(zip(fields, permission)))


def reverse_permissions_load(apps, schema_editor):
    school_permission_class = apps.get_model('lti_school_permissions',
                                             'SchoolPermission')
    school_permission_class.objects.filter(
        canvas_role__in=lti_perm_settings.WHITELISTED_ROLES,
        permission__in=PERMISSION_NAMES,
        school_id__in=lti_perm_settings.SCHOOLS,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('lti_school_permissions', '0003_school_permission_custom_data'),
    ]

    operations = [
        migrations.RunPython(
            code=create_school_default_permissions,
            reverse_code=reverse_permissions_load,
        ),
    ]
