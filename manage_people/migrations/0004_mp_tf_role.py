# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models, transaction

MANAGE_PEOPLE_ROLE_DATA = [
    # NOTE:
    # 1. This is similar to 001_mp_initial. This handles the new TF role(user_role_id=6)
    # 2.this data does not need to vary between environments, as the ids
    #  in the user_role table are the same in both qa and prod oracle
    # (user_role_id, xid_allowed)

    (6, False)
]

# Note:  This is similar to 002_mp_school_allowed_role. This handles TF role
# for the 2 schools that have currently requested it
SCHOOL_ALOWED_ROLE_DATA = [
    ('colgsas', 6, False),
    ('hds', 6, False)
]

def populate_manage_people_role(apps, schema_editor):
    ManagePeopleRole = apps.get_model('manage_people', 'ManagePeopleRole')
    fields = ('user_role_id', 'xid_allowed')
    with transaction.atomic():  # wrap all the inserts in a transaction
        for values in MANAGE_PEOPLE_ROLE_DATA:
            ManagePeopleRole.objects.create(**dict(zip(fields, values)))


def reverse_manage_people_role_load(apps, schema_editor):
    ManagePeopleRole = apps.get_model('manage_people', 'ManagePeopleRole')
    ManagePeopleRole.objects.filter(user_role_id=6).delete()



def populate_school_allowed_role(apps, schema_editor):
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    fields = ('school_id', 'user_role_id', 'xid_allowed')
    with transaction.atomic():  # wrap all the inserts in a transaction
        for values in SCHOOL_ALOWED_ROLE_DATA:
            SchoolAllowedRole.objects.create(**dict(zip(fields, values)))


def reverse_load_school_role(apps, schema_editor):
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    SchoolAllowedRole.objects.filter(user_role_id=6).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('manage_people', '0003_remove_managepeoplerole_canvas_role_label'),

    ]

    operations = [

        migrations.RunPython(
            code=populate_manage_people_role,
            reverse_code=reverse_manage_people_role_load,
        ),

        migrations.RunPython(
            code=populate_school_allowed_role,
            reverse_code=reverse_load_school_role,
        )
    ]
