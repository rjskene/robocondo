# Generated by Django 2.1.3 on 2018-12-23 16:31

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pyyc', '0010_auto_20181216_2116'),
    ]

    operations = [
        migrations.CreateModel(
            name='CurrentForecast',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_added', models.DateTimeField(auto_now_add=True, verbose_name='Date and Time Added')),
                ('date_modified', models.DateTimeField(auto_now=True, verbose_name='Date and Time Modified')),
                ('current', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pyyc.Forecast')),
            ],
        ),
        migrations.AlterField(
            model_name='bocgicforecast',
            name='json',
            field=django.contrib.postgres.fields.jsonb.JSONField(verbose_name='Projected GIC Curve'),
        ),
    ]
