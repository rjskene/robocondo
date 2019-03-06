import time
from decimal import Decimal

from celery import shared_task

from django.db import transaction

from robocondo.celeryconf import app

@shared_task
def analysis_forecast_task(condo_id, study_id, group, curve_id):

    from .models import Forecast
    from .analysis import Converter
    from pyondo.pyondo import Pyondo
    from reservefundstudy.models import Study
    from pyyc.models import BOCGICForecast, Forecast as YCForecast

    converter = Converter(condo_id=condo_id, study_id=study_id, curve_id=curve_id)
    kwargs = converter.make_kwargs()
    invmt_plan = Pyondo(**kwargs)
    model = invmt_plan.pyondo()
    values = invmt_plan.values()

    study = Study.objects.get(pk=study_id)

    with transaction.atomic():
        forecast = Forecast.objects.bulk_create(
            objs=(Forecast(**vals) for vals in values),
            group=group,
            dates=converter.dates
        )

    print ("success!")
    return values
