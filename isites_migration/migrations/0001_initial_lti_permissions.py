# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps as real_apps
from django.db import migrations


LTI_PERMISSIONS = [
    {'permission': 'im_import_files', 'canvas_role': 'Account Observer', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'AccountAdmin', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Account Admin', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Course Head', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Course Support Staff', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Department Admin', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'DesignerEnrollment', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Faculty', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Guest', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Harvard-Viewer', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Help Desk', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Librarian', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'ObserverEnrollment', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'SchoolLiason', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Shopper', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'StudentEnrollment', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'TaEnrollment', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'TeacherEnrollment', 'school_id': '*', 'allow': True},
    {'permission': 'im_import_files', 'canvas_role': 'Teaching Staff', 'school_id': '*', 'allow': True}
]


def create_lti_permissions(apps, schema_editor):
    try:
        LtiPermission = apps.get_model('lti_permissions', 'LtiPermission')
    except LookupError:
        # If the LtiPermission table doesn't exist, return from here
        return

    for permission in LTI_PERMISSIONS:
        lti_permission = LtiPermission(**permission)
        lti_permission.save()


class Migration(migrations.Migration):

    dependencies = []

    # tlt-2650: we need to check whether lti_permissions is part of
    # INSTALLED_APPS and skip this migration if the LtiPermission model is
    # not available.
    if real_apps.is_installed('lti_permissions'):
        dependencies.append(('lti_permissions', '0001_initial'))

    operations = [
        migrations.RunPython(create_lti_permissions)
    ]
