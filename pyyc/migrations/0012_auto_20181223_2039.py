# Generated by Django 2.1.3 on 2018-12-23 20:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pyyc', '0011_auto_20181223_1631'),
    ]

    operations = [
        migrations.RenameField(
            model_name='currentforecast',
            old_name='current',
            new_name='forecast',
        ),
    ]
