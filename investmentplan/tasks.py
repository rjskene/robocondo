import time
from decimal import Decimal

from celery import shared_task

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from robocondo.celeryconf import app

@shared_task(bind=True)
def pyondo_task(self, condo_id, study_id):

    from pyondo.pyondo import Pyondo
    from condo.models import BankAccounts, AccountBalance, Investments
    from reservefundstudy.models import Study, Contributions, Expenditures
    from investmentplan.models import Plan, Forecast
    from investmentplan.converter import Converter
    from pyyc.models import BOCGICForecast
    import gic_select

    self.update_state(
        state="PROGRESS",
    )

    converter = Converter(condo_id=condo_id, study_id=study_id)
    kwargs = converter.make_kwargs()
    invmt_plan = Pyondo(**kwargs)
    model = invmt_plan.pyondo()
    values = invmt_plan.values()

    study = Study.objects.get(pk=study_id)

    with transaction.atomic():
        plan = Plan.objects.create(study=study, time=invmt_plan.result_time())
        forecast = Forecast.objects.bulk_create(
            objs=(Forecast(**vals) for vals in values),
            plan=plan,
            dates=converter.dates
        )
        gic_select.select.select_and_save(values[0], plan)

    return values
