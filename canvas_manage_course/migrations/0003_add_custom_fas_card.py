
import itertools

from django.db import migrations

from lti_school_permissions import settings as lti_perm_settings

# Allow all roles from COLGSAS to access custom card in Manage Course.


NEW_ROLES = [
    'Instructor',
    'Primary Instructor',
    'Secondary Instructor',
    'TF/TA',
    'Faculty Assistant',
    'Preceptor',
    'Course Assistant'
]

# Make a list of all roles
all_roles = lti_perm_settings.WHITELISTED_ROLES + lti_perm_settings.DEFAULT_ROLES + NEW_ROLES


def update_school_permissions(apps, schema_editor):
    school_permission_class = apps.get_model('lti_school_permissions',
                                             'SchoolPermission')

    for role in all_roles:
        school_permission_class(permission='custom_fas_card_1',
                                canvas_role=role,
                                school_id='colgsas').save()


def reverse_permissions_load(apps, schema_editor):
    school_permission_class = apps.get_model('lti_school_permissions',
                                             'SchoolPermission')
    school_permission_class.objects.filter(permission='custom_fas_card_1').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('canvas_manage_course', '0002_add_new_roles'),
    ]

    operations = [
        migrations.RunPython(
            code=update_school_permissions,
            reverse_code=reverse_permissions_load,
        ),
    ]
