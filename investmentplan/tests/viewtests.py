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

from reservefundstudy.models import Study, Contributions, Expenditures
from investmentplan.models import Plan, Forecast
from investmentplan.helpers import int_to_date, find_date

from robocondo.global_helpers import test_data_1, DBTestSetUp

class InvestmentPlanViewTests(TestCase):
    fixtures = ["users.json", "forecasts.json"]

    @classmethod
    def setUpClass(cls):
        super(InvestmentPlanViewTests, cls).setUpClass()
        db_setup = DBTestSetUp(test_data_1, Condo, Study, Contributions, Expenditures, Plan)
        cls.condo, cls.study, cls.conts, cls.exps, cls.plan = db_setup.full_setup()

    def test_visit_reserve_fund_study_and_run_robocondo(self):

        login = self.client.login(username="newuser", password="password123")
        resp = self.client.get(reverse("reservefundstudy:rfs-main", args=("T.S.C.C. 1978", 1, 1)))

        self.assertEqual(str(resp.context["user"]), "newuser")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(reverse("investmentplan:run-robocondo", args=("T.S.C.C. 1978", 1, 1)))
        self.assertEqual(resp.status_code, 302)
