from __future__ import absolute_import
from django.conf import settings

import os

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "robocondo.settings.base")

app = Celery("robocondo",
    include=["investmentplan.tasks", "rcdemo.tasks", "analysis.tasks"]
)

CELERY_TIMEZONE = "UTC"

app.config_from_object(settings, namespace="CELERY")
app.autodiscover_tasks(lambda: settings.ROCO_APPS)
