# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-03-19 10:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('india', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='train',
            name='return_train',
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
    ]
