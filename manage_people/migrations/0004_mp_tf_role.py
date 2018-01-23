# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps as real_apps
from django.db import migrations, models, transaction

MANAGE_PEOPLE_ROLE_DATA = [
    # NOTE:
    # 1. this is similar to 001_mp_initial. This handles the new TF role
    # 2.this data does not need to vary between environments, as the ids
    #  in the user_role table are the same in both qa and prod oracle
    # (user_role_id, xid_allowed)

    (6, False)
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


class Migration(migrations.Migration):
    dependencies = [
        ('manage_people', '0003_remove_managepeoplerole_canvas_role_label'),

    ]

    operations = [

        migrations.RunPython(
            code=populate_manage_people_role,
            reverse_code=reverse_manage_people_role_load,
        )
    ]
