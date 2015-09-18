# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


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
    LtiPermission = apps.get_model('lti_permissions', 'LtiPermission')
    for permission in LTI_PERMISSIONS:
        lti_permission = LtiPermission(**permission)
        lti_permission.save()


class Migration(migrations.Migration):

    dependencies = [
        ('lti_permissions', '0001_initial')
    ]

    operations = [
        migrations.RunPython(create_lti_permissions)
    ]
