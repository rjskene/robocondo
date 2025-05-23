# Generated by Django 2.1.3 on 2018-12-16 21:12

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pyyc', '0008_auto_20181216_1856'),
    ]

    operations = [
        migrations.CreateModel(
            name='BOCGICForecast',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('json', django.contrib.postgres.fields.jsonb.JSONField(verbose_name='Original or Differenced Data')),
                ('last_date', models.DateField(verbose_name='Last Date in Dataset')),
                ('date_added', models.DateTimeField(auto_now_add=True, verbose_name='Date and Time Added')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='Date and Time Modified')),
                ('forecast', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='pyyc.Forecast', unique=True)),
            ],
        ),
    ]
