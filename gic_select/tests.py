import socket
from datetime import datetime as dt, date

from bs4 import BeautifulSoup as bs

from django.test import TestCase, tag, LiveServerTestCase

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from gic_select.models import GICs
from gic_select.select import update_gics, cdic_insured, dico_insured, save_gic_selections

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
from investmentplan.tests.factories import PlanFactory
from pyondo.pyondo import Pyondo

from gic_select.models import GICs, GICPlan, GICSelect
from gic_select.select import select_and_save, gic_select

# This is to update the GIC data from FinancialPost and it requires Selenium!!
@tag("selenium")
class BaseTestCase(LiveServerTestCase):
    """
    Extends LiveServerTestCase so that it works with Selenium hub
    and the various Docker containers
    """

    host = "0.0.0.0"  # Bind to 0.0.0.0 to allow external access

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Set host to externally accessible web server address
        cls.host = socket.gethostbyname(socket.gethostname())

        # Instantiate the remote WebDriver
        cls.chrome = webdriver.Remote(
            command_executor="http://selenium_hub:4444/wd/hub",
            desired_capabilities=DesiredCapabilities.CHROME,
        )
        cls.chrome.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.chrome.quit()
        super().tearDownClass()

@tag("selenium")
class UpdateGICTests(BaseTestCase):

    def test_update_gics_using_selenium(self):
        url = "http://www.financialpost.com/personal-finance/rates/gic-annual.html"
        self.chrome.get(url)
        rows = self.chrome.find_elements_by_tag_name("tr")
        values = []
        for row in rows:
            df = {}
            if row.get_attribute("class") == "heading":
                pass
            elif row.get_attribute("class") == "heading npTxtLeft":
                break
            else:
                cells = row.find_elements_by_tag_name("td")
                df["issuer"] = cells[0].text
                df["date"] = dt.strptime(cells[1].text, "%d %b").replace(year=dt.now().year)
                df["amount"] = cells[2].text
                for i, cell in enumerate(cells[3:]):
                    df["term"] = i + 1
                    df["rate"] = float(cell.text) / 100
                    values.append(df.copy())

        GICs.objects.bulk_create(GICs(**vals) for vals in values)
        gics = GICs.objects.all()

class SelectTests(TestCase):
    fixtures = ["gics.json"]

    @classmethod
    def setUpTestData(self):
        self.invmts = {'term_1': 25000.0, 'term_2': 250000.0, 'term_3': 99000.0, 'term_4': 0.0, 'term_5': 535123.0}
        self.last_date = GICs.objects.latest("date").date
        self.gics = GICs.objects.filter(date=self.last_date)

    def test_find_cdic_insured(self):
        cdic_insured()

    def test_find_dico_insured(self):
        dico_insured()

    def test_gic_select_doesnt_work_with_non_dictionary(self):
        invmts = [("invmts", 1)]
        try:
            new_invmts = gic_select(invmts, self.gics)
        except AssertionError:
            pass

    def test_gic_select_must_have_GICs_object(self):
        gics = {"some": 1, "dict": 2}
        try:
            new_invmts = gic_select(self.invmts, gics)
        except AssertionError:
            pass

    def test_gic_select_must_have_GICs_object_with_only_one_date(self):
        gics = GICs.objects.all()
        try:
            new_invmts = gic_select(self.invmts, gics)
        except ValueError as e:
            if str(e) == "gics object should only contain records from the most recent date":
                pass
            else:
                raise

    def test_new_invmts_allocated_correctly(self):
        new_invmts = gic_select(self.invmts, self.gics)

        # Test amounts allocated are within insurance limits
        max_cdic = 100000
        max_dico = 250000
        for issuer, invmts in new_invmts.items():
            max = max_dico if issuer in dico_insured() else max_cdic
            self.assertTrue(sum(invmts.values()) <= max)

        # Test amount invested in each term is correct
        term_dict = {term: 0 for term, v in self.invmts.items()}
        for issuer, invmts in new_invmts.items():
            for term, amount in invmts.items():
                term_dict[term] += amount
        for term, value in term_dict.items():
            self.assertEqual(value, self.invmts[term])

        # Test total amount invested is correct
        total_invmt = sum(sum(dct.values()) for key, dct in new_invmts.items())
        self.assertEqual(sum(self.invmts.values()), total_invmt)

        # Test result dict is correct
        result = {'Peoples Trust': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'ICICI Bank Canada': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Meridian Credit Union': {'term_1': 0, 'term_2': 0, 'term_3': 99000.0, 'term_4': 0, 'term_5': 0}, 'Investors Group Trust': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Bank of Montreal': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Royal Bank': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Alterna Savings': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 100000}, 'Canadian Tire Bank': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 100000}, 'Canadian Western Trust': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 10123.0}, 'Luminus Financial': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 100000}, 'Bank of Nova Scotia': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Equitable Bank': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Home Bank': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 100000}, 'Sun Life Financial': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Parama Credit Union': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'VersaBank': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Alterna Bank': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 100000}, 'National Bank': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Community Trust': {'term_1': 0, 'term_2': 100000, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'HSBC Bank Canada': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Tangerine': {'term_1': 25000.0, 'term_2': 75000.0, 'term_3': 0, 'term_4': 0.0, 'term_5': 0.0}, 'Effort Trust': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'CIBC': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Manulife Bank': {'term_1': 0, 'term_2': 0, 'term_3': 0, 'term_4': 0, 'term_5': 0}, 'Home Trust': {'term_1': 0, 'term_2': 75000.0, 'term_3': 0, 'term_4': 0, 'term_5': 25000.0}}

        self.assertEqual(new_invmts, result)

    def test_save_gic_selections(self):
        """
        Save GIC recommendaions to GICSelect model
        """
        plan = PlanFactory()

        select_and_save(self.invmts, plan)

        self.assertTrue(GICPlan.objects.get().status_bool)
        self.assertEqual(GICPlan.objects.get().status, "Current")

        last_date = GICs.objects.latest("date").date
        gics = GICs.objects.filter(date=last_date)
        new_invmts = gic_select(self.invmts, gics)

        for record in GICSelect.objects.all():
            self.assertEqual(new_invmts[record.gic.issuer]["term_{}".format(record.gic.term)], record.amount)

        gic_plan2 = GICPlan.objects.create(plan=plan, date=last_date)

        self.assertTrue(gic_plan2.status_bool)
        self.assertEqual(gic_plan2.status, "Current")

        gic_plan = GICPlan.objects.get(pk=1)
        self.assertFalse(gic_plan.status_bool)
        self.assertEqual(gic_plan.status, "Archived")
