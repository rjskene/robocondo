# Generated by Django 2.1.3 on 2018-12-16 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyyc', '0006_auto_20181216_1628'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gics',
            name='date',
            field=models.DateField(verbose_name='Date'),
        ),
    ]
