# -*- coding: utf-8 -*-


from django.db import  migrations, models,transaction
import django.db.models.deletion


SCHOOL_ALOWED_ROLE_DATA = [
    ('gse', 9, False),
    ('gse', 10, True),
    ('gse', 11, False),
    ('gse', 12, False),
    ('gse', 15, True),
    ('colgsas', 9, False),
    ('colgsas', 5, False),
    ('colgsas', 7, False),
    ('colgsas', 10, True),
    ('colgsas', 11, False),
    ('gsd', 5, False),
    ('gsd', 11, False),
    ('gsd', 12, False),
    ('gsd', 10, True),
    ('hds', 9, False),
    ('hds', 5, False),
    ('hds', 7, False),
    ('hds', 10, True),
    ('hds', 11, False),
    ('hds', 12, False),
    ('ext', 9, False),
    ('ext', 5, False),
    ('ext', 7, False),
    ('ext', 10, True),
    ('ext', 11, False),
    ('sum', 9, False),
    ('sum', 5, False),
    ('sum', 7, False),
    ('sum', 10, True),
    ('sum', 11, False),
    ('hks', 5, False),
    ('hks', 10, True),
    ('hls', 5, False),
    ('hls', 7, False),
    ('hls', 10, True),
    ('hls', 11, False),
    ('hls', 12, False),
    ('hlsexeced', 5, False),
    ('hlsexeced', 7, False),
    ('hlsexeced', 9, False),
    ('hlsexeced', 10, True),
    ('hlsexeced', 11, False),
    ('hlsexeced', 12, False),
    ('hlsexeced', 0, False),
    ('hms', 9, False),
    ('hms', 5, False),
    ('hms', 7, False),
    ('hms', 10, True),
    ('hsdm', 9, False),
    ('hsdm', 5, False),
    ('hsdm', 7, False),
    ('hsdm', 10, True),
    ('hsph', 9, False),
    ('hsph', 5, False),
    ('hsph', 7, False),
    ('hsph', 10, True),
    ('hsph', 11, True),
    ('hsph', 12, True),
    ('hsph', 15, True),
    ('hilr', 9, False),
    ('hilr', 5, False),
    ('hilr', 7, False),
    ('hilr', 10, True)
]

def populate_school_allowed_role(apps, schema_editor):
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    fields = ('school_id', 'user_role_id', 'xid_allowed')
    with transaction.atomic():  # wrap all the inserts in a transaction
        for values in SCHOOL_ALOWED_ROLE_DATA:
            SchoolAllowedRole.objects.create(**dict(list(zip(fields, values))))

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
                ('user_role', models.ForeignKey(to='manage_people.ManagePeopleRole', on_delete=django.db.models.deletion.CASCADE)),
                ('xid_allowed', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'school_allowed_role',
                'unique_together': set([('school_id', 'user_role')]),
            },
        ),
        migrations.RunPython(
            code=populate_school_allowed_role,
            reverse_code=reverse_load_school_role,
        ),
    ]
