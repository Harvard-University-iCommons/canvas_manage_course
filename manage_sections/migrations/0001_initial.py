# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
LTI_PERMISSIONS_DATA = [
    ('manage_sections', '*', 'Account Observer', True),
	('manage_sections', '*', 'AccountAdmin', True),
    ('manage_sections', '*', 'Account Admin', True),
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
	('manage_sections', '*', 'Shopper', False),
	('manage_sections', '*', 'StudentEnrollment', False),
	('manage_sections', '*', 'TaEnrollment', True),
	('manage_sections', '*', 'TeacherEnrollment', True),
	('manage_sections', '*', 'Teaching Staff', True),
	('manage_sections', 'colgsas', 'Account Observer', False),
	('manage_sections', 'colgsas', 'DesignerEnrollment', False),
	('manage_sections', 'colgsas', 'Librarian', False),
	('manage_sections', 'dce', 'Account Observer', False),
	('manage_sections', 'dce', 'Librarian', False),
	('manage_sections', 'gse', 'Help Desk', False),
	('manage_sections', 'hks', 'Course Head', False),
	('manage_sections', 'hks', 'Course Support Staff', False),
	('manage_sections', 'hks', 'DesignerEnrollment', False),
	('manage_sections', 'hks', 'Librarian', False),
	('manage_sections', 'hks', 'TaEnrollment', False),
	('manage_sections', 'hks', 'Teaching Staff', False),
	('manage_sections', 'hls', 'Account Observer', False),
	('manage_sections', 'hls', 'Course Head',  False),
	('manage_sections', 'hls', 'Course Support Staff', False),
	('manage_sections', 'hls', 'Department Admin', False),
	('manage_sections', 'hls', 'DesignerEnrollment', False),
	('manage_sections', 'hls', 'Faculty', False),
	('manage_sections', 'hls', 'Help Desk', False),
	('manage_sections', 'hls', 'Librarian', False),
	('manage_sections', 'hls', 'TaEnrollment', False),
	('manage_sections', 'hls', 'TeacherEnrollment', False),
	('manage_sections', 'hls', 'Teaching Staff', False)
]

def create_lti_permissions(apps, schema_editor):
    LtiPermission = apps.get_model('lti_permissions', 'LtiPermission')
    fields = ('permission', 'school_id', 'canvas_role', 'allow')

    for permission in LTI_PERMISSIONS_DATA:
        LtiPermission.objects.create(**dict(zip(fields, permission)))

def reverse_permissions_load(apps, schema_editor):
    LtiPermission = apps.get_model('lti_permissions', 'LtiPermission')
    LtiPermission.objects.filter(permission='manage_sections').delete()

class Migration(migrations.Migration):

    dependencies = [
         ('lti_permissions', '0001_initial'),
    ]

    operations = [

        migrations.RunPython(
            code=create_lti_permissions,
            reverse_code=reverse_permissions_load,
        ),
    ]
