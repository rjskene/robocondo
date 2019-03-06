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
from django.db.models.query import QuerySet
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned


from condo.models import Condo
from condo.helpers import condo_short_name
from condo.tests.factories import CondoFactory, BankAccountsFactory as BAFactory, \
            AccountBalanceFactory as ABFactory, InvestmentsFactory as InvmtsFactory

from reservefundstudy.models import Study, Contributions, Expenditures
from reservefundstudy.tests.factories import StudyFactory, ContributionsFactory as ContFactory, \
            ExpendituresFactory as ExpFactory, cont_kwargs, exp_kwargs
from investmentplan.models import Plan, Forecast
from investmentplan.helpers import find_dates, find_period
from investmentplan.converter import Converter

from robocondo.settings.base import ROCO_APPS

class PyondoConverterDemoModeTests(TestCase):
    fixtures = ["users.json", "pyyc.json"]

    def setUp(self):
        self.contributions = ContFactory(**cont_kwargs)
        self.expenditures = ExpFactory(study=self.contributions.study, **exp_kwargs)
        self.converter = Converter(condo_id=self.contributions.study.condo.id, study_id=self.contributions.study.id, demo=True, naive_rates=True)

    def tearDown(self):
        self.contributions.delete()
        self.contributions.study.delete()
        self.expenditures.delete()

    def test_converter_is_demo(self):
        self.assertTrue(self.converter.demo == True)

    def test_converter_attribute_assignments_for_demo_mode(self):
        self.assertTrue(isinstance(self.converter.condo, Condo))
        self.assertEqual(self.converter.condo, self.contributions.study.condo)
        self.assertTrue(isinstance(self.converter.study, Study))
        self.assertEqual(self.converter.study, self.contributions.study)
        self.assertTrue(isinstance(self.converter.contributions, QuerySet))
        for key, value in self.converter.contributions.values()[0].items():
            if "30" not in key:
                self.assertTrue(value != None)
                self.assertTrue(getattr(self.contributions, key) != None)
            if "30" in key:
                self.assertTrue(value == None)
                self.assertTrue(getattr(self.contributions, key) == None)
            self.assertEqual(value, getattr(self.contributions, key))
        self.assertTrue(isinstance(self.converter.expenditures, QuerySet))
        for key, value in self.converter.expenditures.values()[0].items():
            if "30" not in key:
                self.assertTrue(value != None)
                self.assertTrue(getattr(self.expenditures, key) != None)
            if "30" in key:
                self.assertTrue(value == None)
                self.assertTrue(getattr(self.expenditures, key) == None)
            self.assertEqual(value, getattr(self.expenditures, key))
        self.assertEqual(self.converter.periods, self.contributions.study.years * 12)
        self.assertEqual(self.converter.dates, find_dates(self.contributions.study, self.contributions.study.years * 12))

    def test_get_annual_flows_and_get_monthly_flows_in_demo_mode(self):
        annual_flows = self.converter._get_annual_flows(self.converter.contributions)
        self.assertTrue(isinstance(annual_flows, list))
        self.assertTrue(len(annual_flows) == self.contributions.study.years)
        for index, value in enumerate(annual_flows):
            self.assertEqual(value, getattr(self.contributions, "cont_year_{}".format(index + 1)))
        monthly_flows = self.converter._get_monthly_flows(self.converter.contributions)
        self.assertTrue(isinstance(monthly_flows, list))
        self.assertTrue(len(monthly_flows) == self.contributions.study.years * 12)

    def test_methods_return_none_in_demo_mode(self):
        self.assertTrue(self.converter._get_existing_interest() == None)
        self.assertTrue(self.converter._get_existing_maturities() == None)

    def test_create_kwargs_in_demo_mode(self):
        kwargs = self.converter.make_kwargs()
        self.assertTrue(kwargs["periods"] == self.contributions.study.years * 12)
        self.assertTrue(kwargs["opening_balance"] == self.contributions.study.opening_balance)
        self.assertTrue(kwargs["opening_reserve"] == kwargs["opening_balance"])

        with self.assertRaises(KeyError):
            int =  kwargs["existing_interest"]
            mat = kwargs["existing_maturities"]

    def test_no_negatives(self):
        self.converter.bank_rates = [-0.01 for x in range(self.converter.periods)]
        bank_rates = self.converter._make_zero(self.converter.bank_rates)
        self.assertTrue(all([i >= 0 for i in bank_rates]))

        self.converter.rates = [[0.01, 0.02, 0.03, -0.01, 0.05] for x in range(self.converter.periods)]
        rates = [self.converter._make_zero(period) for period in self.converter.rates]
        flattened = [val for period in rates for val in period]
        self.assertTrue(all([i >= 0 for i in flattened]))

class PyondoConverterRegularMode1Tests(TestCase):
    fixtures = ["users.json", "pyyc.json"]

    def setUp(self):
        self.contributions = ContFactory(**cont_kwargs)
        self.expenditures = ExpFactory(study=self.contributions.study, **exp_kwargs)

    def tearDown(self):
        self.contributions.delete()
        self.contributions.study.delete()
        self.expenditures.delete()

    def test_no_bank_account_raises_error(self):
        with self.assertRaises(ObjectDoesNotExist):
            self.converter = Converter(demo=False, condo_id=self.contributions.study.condo.id, study_id=self.contributions.study.id)

    def test_no_bank_balance_raises_error(self):
        account = BAFactory(condo=self.contributions.study.condo)
        with self.assertRaises(ObjectDoesNotExist):
            self.converter = Converter(demo=False, condo_id=self.contributions.study.condo.id, study_id=self.contributions.study.id)

    def test_attribute_assignments_in_regular_mode(self):
        account = BAFactory(condo=self.contributions.study.condo)
        balance = ABFactory(account=account)
        invmt1 = InvmtsFactory(condo=self.contributions.study.condo)
        invmt2 = InvmtsFactory(condo=self.contributions.study.condo, maturity_date=timezone.make_aware(dt(2021,3,27)))
        invmt3 = InvmtsFactory(condo=self.contributions.study.condo, maturity_date=timezone.make_aware(dt(2014,4,21)))
        self.converter = Converter(demo=False, condo_id=self.contributions.study.condo.id, study_id=self.contributions.study.id)
        self.assertEqual(self.converter.first_period, find_period(self.contributions.study, balance.date))
        self.assertEqual(self.converter.periods, self.contributions.study.years * 12 - find_period(self.contributions.study, balance.date))
        self.assertEqual(self.converter.dates[0].year, balance.date.year)
        self.assertEqual(self.converter.dates[0].month, balance.date.month)
        self.assertEqual(len(self.converter.dates), self.converter.periods)
        for dct in self.converter.investments.values():
            self.assertTrue(dct["maturity_date"] >= balance.date)
        self.assertEqual(self.converter.opening_invmts, invmt1.amount + invmt2.amount)

class PyondoConverterRegularMode2Tests(TestCase):
    fixtures = ["users.json", "pyyc.json"]

    def setUp(self):
        self.contributions = ContFactory(**cont_kwargs)
        self.expenditures = ExpFactory(study=self.contributions.study, **exp_kwargs)
        self.account = BAFactory(condo=self.contributions.study.condo)
        self.balance = ABFactory(account=self.account)
        self.invmt1 = InvmtsFactory(condo=self.contributions.study.condo)
        self.invmt2 = InvmtsFactory(condo=self.contributions.study.condo, maturity_date=timezone.make_aware(dt(2021,3,27)))
        self.converter = Converter(demo=False, condo_id=self.contributions.study.condo.id, study_id=self.contributions.study.id)

    def tearDown(self):
        self.contributions.delete()
        self.contributions.study.delete()
        self.expenditures.delete()
        self.account.delete()
        self.balance.delete()
        self.invmt1.delete()
        self.invmt2.delete()

    def test_monthly_flows_in_regular_mode(self):
        monthly = self.converter._get_monthly_flows(self.converter.contributions)
        period = self.contributions.study.years * 12
        first_period = find_period(self.contributions.study, self.balance.date)
        self.assertEqual(len(monthly), period - first_period)

    def test_get_existing_interest_in_regular_mode(self):
        interest = self.converter._get_existing_interest()
        self.assertTrue(isinstance(interest, dict))
        self.assertEqual(len(interest), 9)
        self.assertTrue(62 in interest and 50 in interest and 38 in interest and 35 in interest)
        self.assertEqual(interest[62], self.invmt1.amount * self.invmt1.interest_rate)

    def test_make_kwargs_in_regular_mode(self):
        kwargs = self.converter.make_kwargs()
        self.assertTrue("existing_interest" in kwargs)
        self.assertTrue("existing_maturities" in kwargs)
        self.assertEqual(kwargs["opening_balance"], self.balance.balance)
        self.assertEqual(kwargs["opening_reserve"], self.balance.balance + self.invmt1.amount + self.invmt2.amount)
