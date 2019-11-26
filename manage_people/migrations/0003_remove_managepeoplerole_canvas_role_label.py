# -*- coding: utf-8 -*-


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('manage_people', '0002_mp_school_allowed_roles'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='managepeoplerole',
            name='canvas_role_label',
        ),
    ]
