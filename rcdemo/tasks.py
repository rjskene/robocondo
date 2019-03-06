import time
from decimal import Decimal

from celery import shared_task

from robocondo.celeryconf import app

@shared_task(bind=True)
def rcdemo_task(self, **conv_kwargs):
    self.update_state(
        state="PROGRESS",
    )

    from rcdemo.demo_converter import DemoConverter
    from investmentplan.converter import Converter
    from pyondo.pyondo import Pyondo

    converter = DemoConverter(**conv_kwargs)
    pyondo_kwargs = converter.make_kwargs()
    invmt_plan = Pyondo(**pyondo_kwargs)
    model = invmt_plan.pyondo()
    forecast = invmt_plan.values()

    return {"forecast": forecast, "study_details": conv_kwargs}
