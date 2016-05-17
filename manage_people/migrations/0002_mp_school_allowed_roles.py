# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import  migrations, models,transaction

SCHOOL_ALOWED_ROLE_DATA = [
    ('gse', 9, 'N'),
    ('gse', 10, 'Y'),
    ('gse', 11, 'N'),
    ('gse', 12, 'N'),
    ('gse', 15, 'Y'),
    ('colgsas', 9, 'N'),
    ('colgsas', 5, 'N'),
    ('colgsas', 7, 'N'),
    ('colgsas', 10, 'Y'),
    ('colgsas', 11, 'N'),
    ('gsd', 5, 'N'),
    ('gsd', 11, 'N'),
    ('gsd', 12, 'N'),
    ('gsd', 10, 'Y'),
    ('hds', 9, 'N'),
    ('hds', 5, 'N'),
    ('hds', 7, 'N'),
    ('hds', 10, 'Y'),
    ('hds', 11, 'N'),
    ('hds', 12, 'N'),
    ('ext', 9, 'N'),
    ('ext', 5, 'N'),
    ('ext', 7, 'N'),
    ('ext', 10, 'Y'),
    ('ext', 11, 'N'),
    ('sum', 9, 'N'),
    ('sum', 5, 'N'),
    ('sum', 7, 'N'),
    ('sum', 10, 'Y'),
    ('sum', 11, 'N'),
    ('hks', 5, 'N'),
    ('hks', 10, 'Y'),
    ('hls', 5, 'N'),
    ('hls', 7, 'N'),
    ('hls', 10, 'Y'),
    ('hls', 11, 'N'),
    ('hls', 12, 'N'),
    ('hlsexeced', 5, 'N'),
    ('hlsexeced', 7, 'N'),
    ('hlsexeced', 9, 'N'),
    ('hlsexeced', 10, 'Y'),
    ('hlsexeced', 11, 'N'),
    ('hlsexeced', 12, 'N'),
    ('hlsexeced', 0, 'N'),
    ('hms', 9, 'N'),
    ('hms', 5, 'N'),
    ('hms', 7, 'N'),
    ('hms', 10, 'Y'),
    ('hsdm', 9, 'N'),
    ('hsdm', 5, 'N'),
    ('hsdm', 7, 'N'),
    ('hsdm', 10, 'Y'),
    ('hsph', 9, 'N'),
    ('hsph', 5, 'N'),
    ('hsph', 7, 'N'),
    ('hsph', 10, 'Y'),
    ('hsph', 11, 'Y'),
    ('hsph', 12, 'Y'),
    ('hsph', 15, 'Y'),
    ('hilr', 9, 'N'),
    ('hilr', 5, 'N'),
    ('hilr', 7, 'N'),
    ('hilr', 10, 'Y')
]

def populate_school_allowed_role(apps, schema_editor):
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    fields = ('school_id', 'user_role_id', 'xid_allowed')
    with transaction.atomic():  # wrap all the inserts in a transaction
        for values in SCHOOL_ALOWED_ROLE_DATA:
            SchoolAllowedRole.objects.create(**dict(zip(fields, values)))

def reverse_load_school_role(apps, schema_editor):
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    SchoolAllowedRole.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('manage_people', '0001_mp_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SchoolAllowedRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('school_id', models.CharField(max_length=10)),
                ('user_role', models.ForeignKey(default=-1, to='manage_people.ManagePeopleRole')),
                ('xid_allowed', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'school_allowed_role',
            },
        ),
        migrations.RunPython(
            code=populate_school_allowed_role,
            reverse_code=reverse_load_school_role,
        ),

    ]