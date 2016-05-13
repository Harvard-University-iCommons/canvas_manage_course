# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models, transaction

'''
NOTE: this migration irrevocably loses all data from the canvas_roles table.
'''


MANAGE_PEOPLE_ROLE_DATA = [
    # NOTE: this data does not need to vary between environments, as the ids
    #       in the user_role table are the same in both qa and prod oracle
    # (user_role_id, canvas_role_label, xid_allowed)
    (0, 'StudentEnrollment', False),
    (1, 'Course Head', False),
    (2, 'Faculty', False),
    (5, 'TaEnrollment', False),
    (7, 'DesignerEnrollment', False),
    (9, 'TeacherEnrollment', False),
    (10, 'Guest', True),
    (11, 'Course Support Staff', False),
    (12, 'Teaching Staff', False),
    (14, 'Shopper', False),
    (15, 'ObserverEnrollment', False)
]


SCHOOL_ALLOWED_ROLE_ID_UPDATE_MAP = {
    # NOTE: this maps old canvas_role_id values to new user_role_id ones.
    #       originally, this was implemented via lookup on the existing
    #       canvas_roles table.  the canvas_role_ids in qa didn't match
    #       the canvas_roles entries in qa, though...they matched the ones
    #       in prod.  so, we use prod canvas_role_ids here.
    # canvas_role_id: user_role_id
    5: 5,
    7: 7,
    9: 9,
    10: 10,
    11: 11,
    12: 12,
    15: 15,
    38: 14,
    90: 0,
    97: 1,
    98: 2,
}
SCHOOL_ALLOWED_ROLE_ID_REVERT_MAP = {
    v:k for k,v in SCHOOL_ALLOWED_ROLE_ID_UPDATE_MAP.iteritems()
}


def populate_manage_people_role(apps, schema_editor):
    ManagePeopleRole = apps.get_model('manage_people', 'ManagePeopleRole')
    fields = ('user_role_id', 'canvas_role_label', 'xid_allowed')
    with transaction.atomic():  # wrap all the inserts in a transaction
        for values in MANAGE_PEOPLE_ROLE_DATA:
            ManagePeopleRole.objects.create(**dict(zip(fields, values)))


def update_school_allowed_role(apps, schema_editor):
    """
    For each role in school_allowed_role, we need to:
    * get the canvas_roles entry it refers to
    * read the canvas_roles.canvas_role value
    * find the matching user_role_id for that canvas_role from our canned
      manage_people_role data we're populating during this migration
    * replace the existing canvas_role_id with the new user_role_id

    NOTE: this expects to be run before the schema change to rename
          school_allowed_role.canvas_role_id to
          school_allowed_role.user_role_id
    """
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    with transaction.atomic():  # wrap all the updates in a transaction
        for sar in SchoolAllowedRole.objects.all():
            sar.canvas_role_id = SCHOOL_ALLOWED_ROLE_ID_UPDATE_MAP[sar.canvas_role_id]
            sar.save()


def revert_school_allowed_role(apps, schema_editor):
    """
    Reverts the changes made in update_school_allowed_role.

    NOTE: this expects to be run after the schema change to rename
          school_allowed_role.user_role_id to
          school_allowed_role.canvas_role_id
    """
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    with transaction.atomic():  # wrap all the updates in a transaction
        for sar in SchoolAllowedRole.objects.all():
            sar.canvas_role_id = SCHOOL_ALLOWED_ROLE_ID_REVERT_MAP[sar.canvas_role_id]
            sar.save()


class Migration(migrations.Migration):
    dependencies = [
        ('manage_people', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManagePeopleRole',
            fields=[
                ('user_role_id', models.IntegerField(primary_key=True)),
                ('canvas_role_label', models.CharField(unique=True, max_length=30)),
                ('xid_allowed', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'manage_people_role',
            },
        ),
        migrations.RunPython(
            code=populate_manage_people_role,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            code=update_school_allowed_role,
            reverse_code=revert_school_allowed_role,
        ),
        migrations.RenameField(
            model_name='schoolallowedrole',
            old_name='canvas_role_id',
            new_name='user_role_id',
        ),
        migrations.AlterUniqueTogether(
            name='schoolallowedrole',
            unique_together=set([('school_id', 'user_role_id')]),
        ),
        migrations.AlterModelTable(
            name='schoolallowedrole',
            table='school_allowed_role',
        ),
        migrations.DeleteModel(
            name='CanvasRoles',
        ),
    ]
