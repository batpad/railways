# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-20 14:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('india', '0006_auto_20160319_1108'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='schedule',
            options={'ordering': ['stop_number', 'minor_stop_number']},
        ),
        migrations.AddField(
            model_name='schedule',
            name='distance_from_previous',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]