from celery import shared_task

from django.db import transaction

from robocondo.celeryconf import app

from .data.update import update_data
from .pyyc.main import PYYC

@shared_task(bind=True)
def update_data_task(self):
    self.update_state(
        state="PROGRESS",
    )
    update_data()

    return

@shared_task(bind=True)
def run_forecast_task(self):
    self.update_state(
        state="PROGRESS",
    )
    pyyc_obj = PYYC()
    pyyc_obj.pyyc()

    return
