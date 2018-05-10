# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models, transaction

MANAGE_PEOPLE_ROLE_DATA = [
    # NOTE:
    # 1. This is similar to 001_mp_initial. This handles the insertion of new set of roles
    # 2. this data does not need to vary between environments, as the ids
    #  in the user_role table are the same in both qa and prod oracle
    # (user_role_id, xid_allowed)


    (18, False),
    (19, False),
    (20, False),
    (21, False),
    (22, False),
    (23, False),
    (24, False),
    (25, False)
]

NEW_ROLE_IDS = [18, 19, 20, 21, 22, 23, 24, 25]

PERMISSION_NAMES = ['canvas_manage_course']

# Note:  This is similar to 002_mp_school_allowed_role. This handles  roles
# for the schools that have currently requested it
SCHOOL_ALOWED_ROLE_DATA = [
    ('hls', 23, False),
    ('hls', 24, False),
    ('hls', 6, False),
    ('hls', 16, False),
    ('hls', 2, False),
    ('hls', 15, False),

]

def populate_manage_people_roles(apps, schema_editor):
    ManagePeopleRole = apps.get_model('manage_people', 'ManagePeopleRole')
    fields = ('user_role_id', 'xid_allowed')
    with transaction.atomic():  # wrap all the inserts in a transaction
        for values in MANAGE_PEOPLE_ROLE_DATA:
            ManagePeopleRole.objects.create(**dict(zip(fields, values)))


def reverse_manage_people_roles_load(apps, schema_editor):
    ManagePeopleRole = apps.get_model('manage_people', 'ManagePeopleRole')
    ManagePeopleRole.objects.filter(user_role_id__in=NEW_ROLE_IDS).delete()



def populate_school_allowed_role(apps, schema_editor):
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    fields = ('school_id', 'user_role_id', 'xid_allowed')
    with transaction.atomic():  # wrap all the inserts in a transaction
        for values in SCHOOL_ALOWED_ROLE_DATA:
            SchoolAllowedRole.objects.create(**dict(zip(fields, values)))


def reverse_load_school_role(apps, schema_editor):
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    # Note that we are only cleaning up the new role ids(and not updates to existing role)
    SchoolAllowedRole.objects.filter(user_role_id__in=NEW_ROLE_IDS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('manage_people', '0004_mp_tf_role'),

    ]

    operations = [

        migrations.RunPython(
            code=populate_manage_people_roles,
            reverse_code=reverse_manage_people_roles_load,
        ),

        migrations.RunPython(
            code=populate_school_allowed_role,
            reverse_code=reverse_load_school_role,
        )
    ]
