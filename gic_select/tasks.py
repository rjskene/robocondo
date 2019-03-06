from celery import shared_task
from celery.exceptions import Ignore


from django.db import transaction, IntegrityError

from robocondo.celeryconf import app

from .select import update_gics

@shared_task(bind=True)
def update_gics_task(self):
    self.update_state(
        state="PROGRESS",
    )

    try:
        update_gics(headless=True)
        return
    except IntegrityError as e:
        if "duplicate key value violates unique constraint" in str(e):
            self.update_state(state="DUPLICATE")
            raise Ignore()
        else:
            raise
