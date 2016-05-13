# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CanvasRoles',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('canvas_role_id', models.IntegerField()),
                ('canvas_role', models.CharField(max_length=20)),
                ('name', models.CharField(max_length=20)),
                ('model_name', models.CharField(max_length=20)),
                ('xid_allowed', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'canvas_roles',
            },
        ),
        migrations.CreateModel(
            name='SchoolAllowedRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('school_id', models.CharField(max_length=10)),
                ('canvas_role_id', models.IntegerField()),
                ('xid_allowed', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'school_allowed_roles',
            },
        ),
        migrations.AlterUniqueTogether(
            name='schoolallowedrole',
            unique_together=set([('school_id', 'canvas_role_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='canvasroles',
            unique_together=set([('canvas_role_id', 'canvas_role')]),
        ),
    ]
