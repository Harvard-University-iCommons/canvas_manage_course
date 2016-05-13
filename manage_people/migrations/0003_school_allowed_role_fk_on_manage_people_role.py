# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def forwards_drop_temp_user_role_id(apps, schema_editor):
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    field = models.IntegerField(name='temp_user_role_id')
    field.set_attributes_from_name('temp_user_role_id')
    schema_editor.remove_field(SchoolAllowedRole, field)


def reverse_drop_temp_user_role_id(apps, schema_editor):
    SchoolAllowedRole = apps.get_model('manage_people', 'SchoolAllowedRole')
    field = models.IntegerField(name='temp_user_role_id', null=True)
    field.set_attributes_from_name('temp_user_role_id')
    schema_editor.add_field(SchoolAllowedRole, field)


class Migration(migrations.Migration):

    dependencies = [
        ('manage_people', '0002_manage_people_uses_coursemanager_user_roles'),
    ]

    operations = [
        migrations.RenameField(
            model_name='schoolallowedrole',
            old_name='user_role_id',
            new_name='temp_user_role_id',
        ),
        migrations.AddField(
            model_name='schoolallowedrole',
            name='user_role',
            field=models.ForeignKey(default=-1, to='manage_people.ManagePeopleRole'),
            preserve_default=False,
        ),
        migrations.RunSQL(
            sql='UPDATE school_allowed_role SET user_role_id=temp_user_role_id',
            reverse_sql='UPDATE school_allowed_role SET temp_user_role_id=user_role_id',
        ),
        migrations.AlterUniqueTogether(
            name='schoolallowedrole',
            unique_together=set([('school_id', 'user_role')]),
        ),
        # since temp_user_role_id isn't actually defined on the model, we can't
        # use migrations.RemoveField directly here.  joy.
        migrations.RunPython(
            code=forwards_drop_temp_user_role_id,
            reverse_code=reverse_drop_temp_user_role_id,
        ),
    ]
