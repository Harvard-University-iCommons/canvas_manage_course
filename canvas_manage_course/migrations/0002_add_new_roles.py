
import itertools

from django.db import migrations

from lti_school_permissions import settings as lti_perm_settings

# Adds new roles to the lti_school_permissions table and removes all isites migration permission records.

NEW_ROLES_MAP = {
    'Faculty': ['Instructor', 'Primary Instructor', 'Secondary Instructor'],
    'TeacherEnrollment': ['TF/TA', 'Faculty Assistant'],
    'Teaching Staff': ['Preceptor'],
    'Student': ['Enrollee'],
    'Prospective Enrollee': ['Petitioner', 'Waitlisted'],
}

PERMISSION_NAMES = ['canvas_manage_course',
                    'class_roster',
                    'manage_people',
                    'manage_sections']

NEW_ROLES = [
    'Instructor',
    'Primary Instructor',
    'Secondary Instructor',
    'TF/TA',
    'Faculty Assistant',
    'Preceptor',
    'Course Assistant'
]


def create_school_permissions(school_permission_class):
    all_permissions = school_permission_class.objects.all()

    # Create the new set of permissions mapped from the current permissions role
    for old_permission in all_permissions:
        try:
            new_roles = NEW_ROLES_MAP[old_permission.canvas_role]
            for new_role in new_roles:
                school_permission_class(permission=old_permission.permission,
                                        canvas_role=new_role,
                                        school_id=old_permission.school_id).save()
        except KeyError:
            # Roles that are not being mapped are not included in the mapping dict and will cause a KeyError
            pass


def update_school_permissions(apps, schema_editor):
    school_permission_class = apps.get_model('lti_school_permissions',
                                             'SchoolPermission')

    # Make sure to rename all Course Head roles to Head Instructor prior to creating the new permissions
    school_permission_class.objects.filter(canvas_role='Course Head').update(canvas_role='Head Instructor')

    create_school_permissions(school_permission_class)

    # The Course Assistant role needs to have just the canvas_manage_course permission in order for the correct
    # 'Not Allowed' message to be displayed.
    for school in lti_perm_settings.SCHOOLS:
        school_permission_class(permission='canvas_manage_course',
                                canvas_role='Course Assistant',
                                school_id=school).save()

    # Remove isites migrations records
    school_permission_class.objects.filter(permission='im_import_files').delete()


def reverse_permissions_load(apps, schema_editor):
    school_permission_class = apps.get_model('lti_school_permissions',
                                             'SchoolPermission')
    school_permission_class.objects.filter(
        canvas_role__in=NEW_ROLES,
        permission__in=PERMISSION_NAMES,
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
