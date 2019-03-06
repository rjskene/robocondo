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

from condo.models import Condo
from condo.helpers import condo_short_name

from pyondo.pyondo import Pyondo

from condo.models import Condo, Investments
from reservefundstudy.models import Study, Contributions, Expenditures
from investmentplan.models import Plan, Forecast
from investmentplan.helpers import int_to_date, find_date
from investmentplan.converter import Converter

from condo.tests.factories import CondoFactory, BankAccountsFactory as BAFactory, \
                    AccountBalanceFactory as ABFactory, InvestmentsFactory as InvmtsFactory

from investmentplan.tests.factories import PlanFactory
from reservefundstudy.tests.factories import StudyFactory, ContributionsFactory as ContFactory, \
            ExpendituresFactory as ExpFactory, cont_kwargs, exp_kwargs
import gic_select
from gic_select.models import GICs, GICSelect, GICPlan

from robocondo.global_helpers import test_data_1, DBTestSetUp
from robocondo.settings.base import ROCO_APPS

def plan_maker(study=None, invmts=False, spread=None, naive_rates=False):
    plan = PlanFactory() if not study else PlanFactory(study=study)
    conts = ContFactory(study=plan.study, **cont_kwargs)
    exps = ExpFactory(study=plan.study, **exp_kwargs)
    acct = BAFactory(condo=plan.study.condo)
    bal = ABFactory(account=acct)
    invmts = InvmtsFactory(condo=plan.study.condo) if invmts else None
    converter = Converter(condo_id=conts.study.condo.id, study_id=conts.study.id, spread=spread, naive_rates=naive_rates)
    kwargs = converter.make_kwargs()
    invmt_plan = Pyondo(**kwargs)
    model = invmt_plan.pyondo()
    values = invmt_plan.values(model)
    return {
            "values":values, "plan": plan,
            "converter": converter, "bal": bal,
            "kwargs": kwargs
    }

class CreateNewForecastBankAccountNoInvestmentsTests(TestCase):
    fixtures = ["users.json", "pyyc.json"]

    @classmethod
    def setUpTestData(self):
        self.plan_objs = plan_maker()

    @override_settings(
        DEBUG=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPOGATES=True,
    )
    def test_forecast_account_no_invmts(self):
        # Bank Account Date: 2018-5-14
        # Periods: 344
        # Bank Balance: 125000
        # Total Invesment: 125000
        Forecast.objects.bulk_create(
            objs=(Forecast(**vals) for vals in self.plan_objs["values"]),
            plan=self.plan_objs["plan"],
            dates=self.plan_objs["converter"].dates
        )

        forecast = Forecast.objects.filter(plan=self.plan_objs["plan"])

        self.assertEqual(forecast.filter(period=1).values("month")[0]["month"],
            timezone.make_aware(dt(year=self.plan_objs["bal"].date.year,
                                month=self.plan_objs["bal"].date.month,
                                day=1)
            )
        )
        months = [row.month for row in forecast]
        for idx, val in enumerate(months):
            self.assertEqual(months[idx], self.plan_objs["converter"].dates[idx])

        for row in forecast:
            self.assertEqual(row.plan, self.plan_objs["plan"])

        self.assertEqual(self.plan_objs["plan"].status, "Current")
        self.assertTrue(self.plan_objs["plan"].status_bool)

        self.assertEqual(forecast.count(), len(self.plan_objs["values"]))
        self.assertEqual(forecast.count(), self.plan_objs["kwargs"]["periods"])

        self.assertEqual(forecast[0].opening_balance, self.plan_objs["kwargs"]["opening_reserve"])

        for row in forecast:
            self.assertEqual(round(row.total_investments, 2), round((row.term_1 + row.term_2 + row.term_3 + row.term_4 + row.term_5), 2))

class CreateNewForecastBankAccountAndInvestmentsTests(TestCase):
    fixtures = ["users.json", "pyyc.json"]

    @classmethod
    def setUpTestData(self):
        self.plan_objs = plan_maker(invmts=True)

    @override_settings(
        DEBUG=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPOGATES=True,
    )
    def test_forecast_account_and_invmts(self):
        # Bank Account Date: 2018-5-14
        # Periods: 344
        # Bank Balance: 125000
        # Investment: $100000
        # Total Invesment: 225000
        Forecast.objects.bulk_create(
            objs=(Forecast(**vals) for vals in self.plan_objs["values"]),
            plan=self.plan_objs["plan"],
            dates=self.plan_objs["converter"].dates
        )

        forecast = Forecast.objects.filter(plan=self.plan_objs["plan"])

        self.assertEqual(forecast.filter(period=1).values("month")[0]["month"],
            timezone.make_aware(dt(year=self.plan_objs["bal"].date.year,
                                month=self.plan_objs["bal"].date.month,
                                day=1)
            )
        )
        months = [row.month for row in forecast]
        for idx, val in enumerate(months):
            self.assertEqual(months[idx], self.plan_objs["converter"].dates[idx])

        for row in forecast:
            self.assertEqual(row.plan, self.plan_objs["plan"])

        self.assertEqual(self.plan_objs["plan"].status, "Current")
        self.assertTrue(self.plan_objs["plan"].status_bool)

        self.assertEqual(forecast.count(), len(self.plan_objs["values"]))
        self.assertEqual(forecast.count(), self.plan_objs["kwargs"]["periods"])

        self.assertEqual(forecast[0].opening_balance, self.plan_objs["kwargs"]["opening_reserve"])

        for row in forecast:
            self.assertEqual(round(row.total_investments, 2), round((row.term_1 + row.term_2 + row.term_3 + row.term_4 + row.term_5), 2))


class AddMultipleInvestmentPlansTests(TestCase):
    """
    Creating multiple investment plans
    Test is if previous investment plans are re-classified as Archived
    """
    fixtures = ["users.json", "pyyc.json"]

    @classmethod
    def setUpTestData(self):
        self.plan_objs1 = plan_maker(spread=0.03)
        self.plan_objs2 = plan_maker(study=self.plan_objs1["plan"].study, spread=0.03)

    @override_settings(
        DEBUG=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPOGATES=True,
    )
    def test_current_or_archived_status_for_plan(self):
        for row in self.plan_objs1["values"]:
            row["plan"] = self.plan_objs1["plan"]

        fore1 = Forecast.objects.bulk_create(
            objs=(Forecast(**vals) for vals in self.plan_objs1["values"]),
            plan=self.plan_objs1["plan"],
            dates=self.plan_objs1["converter"].dates
        )

        for row in self.plan_objs2["values"]:
            row["plan"] = self.plan_objs2["plan"]

        fore2 = Forecast.objects.bulk_create(
            objs=(Forecast(**vals) for vals in self.plan_objs2["values"]),
            plan=self.plan_objs2["plan"],
            dates=self.plan_objs2["converter"].dates
        )

        fore1_new = Forecast.objects.filter(plan=fore1[0].plan)

        self.assertEqual(self.plan_objs2["plan"].status, "Current")
        self.assertTrue(self.plan_objs2["plan"].status_bool)

        self.assertEqual(fore1_new[0].plan.status, "Archived")
        self.assertFalse(fore1_new[0].plan.status_bool)
