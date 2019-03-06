import time
import inspect
from operator import sub
from datetime import datetime as dt, date
from dateutil.relativedelta import relativedelta
from pyomo.core.base.PyomoModel import ConcreteModel

from django.utils import timezone
from django.test import TestCase
from django.test.utils import override_settings

from condo.models import Condo, BankAccounts
from condo.helpers import condo_short_name
from condo.tests.factories import CondoFactory, BankAccountsFactory as BAFactory, \
            AccountBalanceFactory as ABFactory, InvestmentsFactory as InvmtsFactory

from reservefundstudy.models import Study, Contributions, Expenditures
from reservefundstudy.tests.factories import StudyFactory, ContributionsFactory as ContFactory, \
            ExpendituresFactory as ExpFactory, cont_kwargs, exp_kwargs
from investmentplan.models import Plan, Forecast
from investmentplan.helpers import find_dates, find_period
from investmentplan.converter import Converter

from .pyondo import Pyondo

class PyondoInitializationTests(TestCase):
    fixtures = ["users.json", "forecasts.json"]

    @classmethod
    def setUpTestData(cls):
        """
        These tests are in DEMO MODE
        """
        cls.contributions = ContFactory(**cont_kwargs)
        cls.expenditures = ExpFactory(study=cls.contributions.study, **exp_kwargs)
        cls.converter = Converter(condo_id=cls.contributions.study.condo.id, study_id=cls.contributions.study.id, spread=0.03)
        cls.values = cls.converter.make_kwargs()
        cls.rqrd_keys = [
            "periods", "contributions", "expenditures", "opening_balance",
             "opening_reserve", "rates", "bank_rates"
        ]
        cls.opt_keys = ["existing_interest", "existing_maturities"]
        cls.rqrd_types = {
            "existing_interest": dict, "existing_maturities": dict,
            "periods": int, "contributions": list, "expenditures": list,
            "rates": list, "bank_rates": list,
            "opening_balance": float, "opening_reserve": float
        }
        cls.output_keys = ['period', 'opening_balance', 'contributions', 'expenditures',
            'interest', 'closing_balance', 'bank_balance', 'current_investments',
            'maturities', 'term_1', 'term_2', 'term_3', 'term_4', 'term_5', 'total_investments'
        ]
        cls.account = BAFactory(condo=cls.contributions.study.condo)
        # print (BankAccounts.objects.filter(condo=cls.contributions.study.condo))
        cls.balance = ABFactory(account=cls.account)
        cls.invmts2 = InvmtsFactory(condo=cls.contributions.study.condo)
        cls.converter2 = Converter(condo_id=cls.contributions.study.condo.id, study_id=cls.contributions.study.id, demo=False)
        cls.values2 = cls.converter2.make_kwargs()

    def test_correct_constants_in_init(self):
        self.assertTrue(Pyondo.CONSTANTS["REQUIRED_KEYS"] == self.rqrd_keys)
        self.assertEqual(Pyondo.CONSTANTS["OPTIONAL_KEYS"], self.opt_keys)
        self.assertTrue(Pyondo.CONSTANTS["REQUIRED_TYPES"] == self.rqrd_types)
        self.assertEqual(Pyondo.CONSTANTS["MINIMUM_BANK_BALANCE"], 100000)
        self.assertEqual(Pyondo.CONSTANTS["MinIA"], 25000)
        self.assertEqual(Pyondo.CONSTANTS["MaxIA"], 10000000)
        self.assertEqual(Pyondo.CONSTANTS["TERMS"], 5)
        self.assertEqual(Pyondo.CONSTANTS["BLP"], 0.005 / 12)

    def test_correct_initialization(self):
        self.pyondo_setup = Pyondo(**self.values)
        method_list = [func for func in dir(Pyondo) if callable(getattr(Pyondo, func)) and not func.startswith("__")]

        for attr in dir(self.pyondo_setup):
            if (not attr.startswith("__") and not attr.startswith("_") and attr not in method_list
                and attr != "CONSTANTS"):
                if (attr == "existing_interest" or attr == "existing_maturities"):
                    self.assertEqual(getattr(self.pyondo_setup, attr), None)
                else:
                    self.assertEqual(getattr(self.pyondo_setup, attr), self.values[attr])
        self.assertEqual(self.pyondo_setup._find_net_cash_flow(),
            list(map(sub, self.values["contributions"], self.values["expenditures"])))

    def test_same_length(self):
        self.pyondo_setup = Pyondo(**self.values)
        self.assertTrue(self.pyondo_setup._same_length(**self.values))
        self.values["contributions"].append("not same")
        self.assertFalse(self.pyondo_setup._same_length(**self.values))

    def test_initialization_exceptions(self):
        self.values["contributions"].append("not same")
        with self.assertRaises(ValueError):
            self.pyondo_setup = Pyondo(**self.values)
        self.values["contributions"].remove("not same")
        self.values["new key"] = "some new key"
        with self.assertRaises(IndexError):
            self.pyondo_setup = Pyondo(**self.values)
        del self.values["new key"]
        self.values["periods"] = [1,2,3,4]
        with self.assertRaises(TypeError):
            self.pyondo_setup = Pyondo(**self.values)
        self.values["periods"] = self.contributions.study.years * 12

    def test_correct_initialization_with_existing_int_and_maturities(self):
        pyondo_setup = Pyondo(**self.values2)
        method_list = [func for func in dir(Pyondo) if callable(getattr(Pyondo, func)) and not func.startswith("__")]

        for attr in dir(pyondo_setup):
            if (not attr.startswith("__") and not attr.startswith("_")
                and attr not in method_list and attr != "CONSTANTS"):
                self.assertEqual(getattr(pyondo_setup, attr), self.values2[attr])
        self.assertEqual(pyondo_setup._find_net_cash_flow(),
            list(map(sub, self.values2["contributions"], self.values2["expenditures"])))

    def test_pyondo_output(self):
        pyondo_setup = Pyondo(**self.values)
        pyondo_setup2 = Pyondo(**self.values2)
        model = pyondo_setup.pyondo()
        model2 = pyondo_setup2.pyondo()
        self.assertTrue(isinstance(model, ConcreteModel))
        output = pyondo_setup.values(model)
        output2 = pyondo_setup2.values(model2)

        self.assertTrue(isinstance(output, list))
        self.assertTrue(isinstance(output2, list))
        self.assertEqual(len(output), self.contributions.study.years * 12)
        self.assertEqual(len(output2), len(self.values2["contributions"]))
        for dct in output:
            for k, v in dct.items():
                self.assertTrue(k in self.output_keys)
            self.assertTrue(isinstance(dct, dict))
