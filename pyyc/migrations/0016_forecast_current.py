# Generated by Django 2.1.3 on 2019-01-01 02:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyyc', '0015_auto_20181230_1420'),
    ]

    operations = [
        migrations.AddField(
            model_name='forecast',
            name='current',
            field=models.BooleanField(default=False, verbose_name='Current Forecast Used for Projections?'),
        ),
    ]
