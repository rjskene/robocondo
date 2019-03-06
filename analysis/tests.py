import time
import socket
from datetime import datetime as dt, date
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from django.utils import timezone
from django.urls import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.test.client import Client
from django.contrib.auth.models import User

from .models import Forecast
from .analysis import Converter
from condo.tests.factories import CondoFactory, BankAccountsFactory as BAFactory, \
                    AccountBalanceFactory as ABFactory, InvestmentsFactory as InvmtsFactory

from investmentplan.tests.factories import PlanFactory
from reservefundstudy.tests.factories import StudyFactory, ContributionsFactory as ContFactory, \
            ExpendituresFactory as ExpFactory, cont_kwargs, exp_kwargs

def plan_maker(study=None, invmts=False, spread=None, naive_rates=False):
    plan = PlanFactory() if not study else PlanFactory(study=study)
    conts = ContFactory(study=plan.study, **cont_kwargs)
    exps = ExpFactory(study=plan.study, **exp_kwargs)
    acct = BAFactory(condo=plan.study.condo)
    bal = ABFactory(account=acct)
    invmts = InvmtsFactory(condo=plan.study.condo) if invmts else None
    converter = Converter(condo_id=conts.study.condo.id, study_id=conts.study.id)
    kwargs = converter.make_kwargs()
    invmt_plan = Pyondo(**kwargs)
    model = invmt_plan.pyondo()
    values = invmt_plan.values(model)
    return {
            "values":values, "plan": plan,
            "converter": converter, "bal": bal,
            "kwargs": kwargs
    }

class AnalysisTests(TestCase):
    # fixtures = ["users.json", "pyyc.json"]

    @classmethod
    def setUpTestData(self):
        self.plan_objs = plan_maker()

    @override_settings(
        DEBUG=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPOGATES=True,
    )
    def test_forecast_account_no_invmts(self):

        Forecast.objects.bulk_create(
            objs=(Forecast(**vals) for vals in self.plan_objs["values"]),
            plan=self.plan_objs["plan"],
            dates=self.plan_objs["converter"].dates
        )
