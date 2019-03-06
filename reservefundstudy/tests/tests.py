from django.test import TestCase

import time
import socket
from datetime import datetime as dt, date
import pandas as pd

from django.urls import reverse

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, tag, LiveServerTestCase
from django.test.utils import override_settings
from django.test.client import Client
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from guardian.shortcuts import get_objects_for_user, assign_perm

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from reservefundstudy.tests.factories import StudyFactory, ContributionsFactory, ExpendituresFactory
from reservefundstudy.models import Study, Contributions, Expenditures, YEAR_CHOICES
from reservefundstudy.helpers import make_cont_and_exp_table, find_included_years

from condo.models import Condo
from condo.tests.factories import CondoFactory

from investmentplan.models import Plan
from investmentplan.tests.factories import PlanFactory
from condo.helpers import condo_short_name

from robocondo.settings.base import ROCO_APPS

path = "/code/reservefundstudy/tests/rfs.csv"

@tag("selenium")
class BaseTestCase(StaticLiveServerTestCase):
    """
    Extends StaticLiveServerTestCase so that it works with Selenium hub
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

# @tag("selenium")
# @override_settings(DEBUG=True)
# class AddFirstReserveFundStudyViewTests(BaseTestCase):
#
#     fixtures = ["users.json"]
#
#     def setUp(cls):
#         cls.user = User.objects.get(username="Spindicate")
#         cls.condo = CondoFactory()
#         assign_perm("view_condo", cls.user, cls.condo)
#
#         cls.study = {
#                 "date": "14-02-2014",
#                 "first_year": 2012,
#                 "last_year": 2040,
#                 "years": 39,
#                 "opening_balance": 733330,
#                 "current": True
#         }
#
#     def test_user_permission_true(self):
#         self.assertTrue(self.user.has_perm("view_condo", self.condo))
#
#     def test_visit_condo_main_and_create_new_reserve_fund_study_using_file_upload(self):
#         self.chrome.get("{}".format(self.live_server_url) + "/login/")
#         username_input = self.chrome.find_element_by_name("username")
#         username_input.send_keys(self.user.username)
#         password_input = self.chrome.find_element_by_name("password")
#         password_input.send_keys("Calgary1")
#         self.chrome.find_element_by_xpath("//button[@type='submit']").click()
#
#         # Check if Condo exists in list
#         condo = self.chrome.find_element_by_link_text(self.condo.name)
#         self.assertIn(self.condo.name, condo.text)
#
#         self.chrome.find_element_by_link_text(self.condo.name).click()
#
#         # Check if dashboard loads correctly
#         subtitle = self.chrome.find_element_by_xpath("//div[@id='condo_subtitle']")
#         subtitle_value = subtitle.get_attribute("value")
#         self.assertIn("CondoSubtitle", subtitle_value)
#
#         # Check if return link works correctly
#         self.chrome.find_element_by_id("dashboard_sidebar").click()
#         condo = self.chrome.find_element_by_link_text(self.condo.name)
#         self.assertIn(self.condo.name, condo.text)
#
#         self.chrome.find_element_by_link_text(self.condo.name).click()
#
#         # Test reserve fund study form submission
#         self.chrome.find_element_by_id("createNewStudyTrigger").click()
#         date_input = self.chrome.find_element_by_xpath("//input[@name='date']")
#         date_input.clear()
#         date_input.send_keys(self.study["date"])
#         first_input = self.chrome.find_element_by_xpath("//input[@name='current']").click()
#         first_input = self.chrome.find_element_by_xpath("//select[@name='first_year']")
#         first_input.send_keys(self.study["first_year"])
#         last_input = self.chrome.find_element_by_xpath("//select[@name='last_year']")
#         last_input.send_keys(self.study["last_year"])
#         opening_input = self.chrome.find_element_by_xpath("//input[@name='opening_balance']")
#         opening_input.clear()
#         opening_input.send_keys(self.study["opening_balance"])
#
#         upload = self.chrome.find_element_by_xpath("//input[@name='file']")
#         upload.send_keys(path)
#
#         self.chrome.find_element_by_xpath("//input[@name='create_study_form']").click()
#
#         studies = Study.objects.all()
#         study = studies[0]
#
#         # Test model updated correctly
#         self.assertTrue(studies.exists())
#         self.assertTrue(study.opening_balance == float(self.study["opening_balance"]))
#         self.assertTrue(study.first_year == self.study["first_year"])
#         self.assertIn(study.first_year, dict(YEAR_CHOICES))
#         self.assertTrue(study.last_year == self.study["last_year"])
#         self.assertIn(study.last_year, dict(YEAR_CHOICES))
#         self.assertTrue(study.years == study.last_year - study.first_year + 1)
#         self.assertTrue(study.condo.name == self.condo.name)
#         self.assertTrue(study.date == dt.strptime(self.study["date"], "%d-%m-%Y").date())
#
#         study_link = self.chrome.find_element_by_id("submit_success")
#         self.assertTrue(study_link)

    # def test_visit_condo_main_and_create_reserve_fund_study_using_conts_exps_table(self):
    #     self.chrome.get("{}".format(self.live_server_url) + "/login/")
    #     username_input = self.chrome.find_element_by_name("username")
    #     username_input.send_keys(self.user.username)
    #     password_input = self.chrome.find_element_by_name("password")
    #     password_input.send_keys("Calgary1")
    #     self.chrome.find_element_by_xpath("//button[@type='submit']").click()
    #
    #     # Check if Condo exists in list
    #     condo = self.chrome.find_element_by_link_text(self.condo.name)
    #     self.assertIn(self.condo.name, condo.text)
    #
    #     self.chrome.find_element_by_link_text(self.condo.name).click()
    #
    #     # Check if dashboard loads correctly
    #     body = self.chrome.find_element_by_xpath("//body")
    #     self.assertIn("This is the main dashboard for the Condo", body.text)
    #
    #     # Check if return link works correctly
    #     self.chrome.find_element_by_link_text("Go to your Dashboard").click()
    #     body = self.chrome.find_element_by_xpath("//body")
    #     self.assertIn("This is the User dashboard", body.text)
    #
    #     self.chrome.find_element_by_link_text(self.condo.name).click()
    #
    #     # Test reserve fund study form submission
    #     self.chrome.find_element_by_link_text("Click Here to Create New Reserve Fund Study").click()
    #     date_input = self.chrome.find_element_by_xpath("//input[@name='date']")
    #     date_input.send_keys("14-02-2014")
    #     first_input = self.chrome.find_element_by_xpath("//select[@name='first_year']")
    #     first_input.send_keys(self.study.first_year)
    #     last_input = self.chrome.find_element_by_xpath("//select[@name='last_year']")
    #     last_input.send_keys(self.study["last_year"])
    #     opening_input = self.chrome.find_element_by_xpath("//input[@name='opening_balance']")
    #     opening_input.clear()
    #     opening_input.send_keys(self.study["opening_balance"])
    #
    #     self.chrome.find_element_by_xpath("//input[@type='submit']").click()
    #
    #     studies = Study.objects.all()
    #     study = studies[0]
    #     included_years = find_included_years(study)
    #     conts_exps = list(zip(self.contributions, self.expenditures))
    #     inputs = dict(zip(included_years, conts_exps))
    #
    #     # Test model updated correctly
    #     self.assertTrue(studies.exists())
    #     self.assertTrue(study.opening_balance == float(self.study["opening_balance"]))
    #     self.assertTrue(study.first_year == self.study["first_year"])
    #     self.assertIn(study.first_year, dict(YEAR_CHOICES))
    #     self.assertTrue(study.last_year == self.study["last_year"])
    #     self.assertIn(study.last_year, dict(YEAR_CHOICES))
    #     self.assertTrue(study.years == study.last_year - study.first_year + 1)
    #     self.assertTrue(study.condo.name == self.condo.name)
    #     self.assertTrue(study.date == dt.strptime(self.study["date"], "%Y-%m-%d").date())
    #
    #     # Test Contributions and Expenditures input correctly
    #     for year, values in inputs.items():
    #         cont_input = self.chrome.find_element_by_xpath("//input[@name='cont_{}']".format(year))
    #         cont_input.send_keys(values[0])
    #         exp_input = self.chrome.find_element_by_xpath("//input[@name='exp_{}']".format(year))
    #         exp_input.send_keys(values[1])
    #
    #     self.chrome.find_element_by_xpath("//input[@type='submit']").click()
    #
    #     study_link = self.chrome.find_element_by_link_text("Feb. 14, 2014")
    #     self.assertTrue(study_link)

@tag("selenium")
@override_settings(DEBUG=True)
class AddFirstReserveFundStudyViewTests(BaseTestCase):

    fixtures = ["users.json"]

    def setUp(cls):
        cls.user = User.objects.get(username="Spindicate")
        cls.condo = CondoFactory()
        assign_perm("view_condo", cls.user, cls.condo)

        cls.study = {
                "date": "14-02-2014",
                "first_year": 2012,
                "last_year": 2040,
                "years": 39,
                "opening_balance": 733330,
                "current": True
        }

    def test_user_permission_true(self):
        self.assertTrue(self.user.has_perm("view_condo", self.condo))

    def test_visit_condo_main_and_create_new_reserve_fund_study_using_file_upload(self):
        self.chrome.get("{}".format(self.live_server_url) + "/login/")
        username_input = self.chrome.find_element_by_name("username")
        username_input.send_keys(self.user.username)
        password_input = self.chrome.find_element_by_name("password")
        password_input.send_keys("Calgary1")
        self.chrome.find_element_by_xpath("//button[@type='submit']").click()

        # Check if Condo exists in list
        condo = self.chrome.find_element_by_link_text(self.condo.name)
        self.assertIn(self.condo.name, condo.text)

        self.chrome.find_element_by_link_text(self.condo.name).click()

        # Check if dashboard loads correctly
        subtitle = self.chrome.find_element_by_xpath("//div[@id='condo_subtitle']")
        subtitle_value = subtitle.get_attribute("value")
        self.assertIn("CondoSubtitle", subtitle_value)

        # Check if return link works correctly
        self.chrome.find_element_by_id("dashboard_sidebar").click()
        condo = self.chrome.find_element_by_link_text(self.condo.name)
        self.assertIn(self.condo.name, condo.text)

        self.chrome.find_element_by_link_text(self.condo.name).click()

        # Test reserve fund study form submission
        self.chrome.find_element_by_id("createNewStudyTrigger").click()
        date_input = self.chrome.find_element_by_xpath("//input[@name='date']")
        date_input.clear()
        date_input.send_keys(self.study["date"])
        first_input = self.chrome.find_element_by_xpath("//input[@name='current']").click()
        first_input = self.chrome.find_element_by_xpath("//select[@name='first_year']")
        first_input.send_keys(self.study["first_year"])
        last_input = self.chrome.find_element_by_xpath("//select[@name='last_year']")
        last_input.send_keys(self.study["last_year"])
        opening_input = self.chrome.find_element_by_xpath("//input[@name='opening_balance']")
        opening_input.clear()
        opening_input.send_keys(self.study["opening_balance"])

        upload = self.chrome.find_element_by_xpath("//input[@name='file']")
        upload.send_keys(path)

        self.chrome.find_element_by_xpath("//input[@name='create_study_form']").click()

        studies = Study.objects.all()
        study = studies[0]

        # Test model updated correctly
        self.assertTrue(studies.exists())
        self.assertTrue(study.opening_balance == float(self.study["opening_balance"]))
        self.assertTrue(study.first_year == self.study["first_year"])
        self.assertIn(study.first_year, dict(YEAR_CHOICES))
        self.assertTrue(study.last_year == self.study["last_year"])
        self.assertIn(study.last_year, dict(YEAR_CHOICES))
        self.assertTrue(study.years == study.last_year - study.first_year + 1)
        self.assertTrue(study.condo.name == self.condo.name)
        self.assertTrue(study.date == dt.strptime(self.study["date"], "%d-%m-%Y").date())

        study_link = self.chrome.find_element_by_id("submit_success")
        self.assertTrue(study_link)

class ReserveFundStudyModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.condo_data = {
                        "name": "Toronto Standard Condominium Corporation 1978",
        }
        cls.condo = Condo.objects.create(**cls.condo_data)
        cls.study = {
                                "condo": cls.condo,
                                "date": "2014-02-14",
                                "first_year": 2012,
                                "last_year": 2040,
                                "years": 2040 - 2012 + 1,
                                "opening_balance": 733330,
        }
        cls.study = Study.objects.create(**cls.study)
        cls.contributions = [
                        203000, 210000, 243600,282576,327788,380234,441072,511643,
                        593506,688467,702236,716281,730607,745219,760123,775326,
                        790832,806649,822782,839238,856022,873143,890606,908418,
                        926586,945118,964020,983301,1002967
        ]
        cls.expenditures = [
                        223841,489283,12293,17139,12602,535790,34068,534489,
                        13245,314291,600049,0,235115,650744,0,4976504,855760,0,
                        5653,605227,3094391,5867,560439,352020,272911,3491946,
                        749187,406295,0
        ]

    def test_name_label(self):
        studies = Study.objects.all()
        study = studies[0]
        field_label = study._meta.get_field("date").verbose_name
        self.assertEquals(field_label, "Date of Reserve Fund Study")

        field_label = study._meta.get_field("first_year").verbose_name
        self.assertEquals(field_label, "First Year of Study")
        self.assertIn(study.first_year, dict(YEAR_CHOICES))

        field_label = study._meta.get_field("last_year").verbose_name
        self.assertEquals(field_label, "Last Year of Study")
        self.assertIn(study.last_year, dict(YEAR_CHOICES))

        field_label = study._meta.get_field("years").verbose_name
        self.assertEquals(field_label, "Number of Years in Study")
        self.assertEqual(study.years, study.last_year - study.first_year + 1)

        field_label = study._meta.get_field("opening_balance").verbose_name
        self.assertEquals(field_label, "Opening Balance")

        field_label = study._meta.get_field("date_added").verbose_name
        self.assertEquals(field_label, "Date and Time Added")
        self.assertEquals(study.date_added.date(), dt.now().date())

        field_label = study._meta.get_field("date_modified").verbose_name
        self.assertEquals(field_label, "Date and Time Modified")
        self.assertEquals(study.date_modified.date(), dt.now().date())


# SHOULD BE IN MODEL TESTS!
# Test OnetoOneField on Conts and Exps
# try:
#     conts = Contributions(study=study)
#     conts.save()
# except IntegrityError as e:
#     if "duplicate key value violates unique constraint" in str(e) and \
#         "DETAIL:  Key (study_id)=" in str(e):
#         pass
#     else:
#         raise
# try:
#     exps = Expenditures(study=study)
#     exps.save()
# except IntegrityError as e:
#     if "duplicate key value violates unique constraint" in str(e) and \
#         "DETAIL:  Key (study_id)=" in str(e):
#         pass
#     else:
#         raise
