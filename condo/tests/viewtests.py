from django.test import TestCase

import time
import socket
from datetime import datetime as dt

from django.urls import reverse

from django.test import TestCase, tag, LiveServerTestCase
from django.test.utils import override_settings
from django.test.client import Client
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from decouple import config

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from condo.models import Condo, BankAccounts, AccountBalance, Investments

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

@tag("selenium")
class AddNewCondoTests(BaseTestCase):
    fixtures = ["users.json"]

    def setUp(cls):
        cls.condo_data = {
                        "name": "Toronto Standard Condominium Corporation 1978",
        }

    def test_visit_condo_main_and_create_new_condo(self):
        self.chrome.get("{}".format(self.live_server_url) + "/login/")
        username_input = self.chrome.find_element_by_name("username")
        username_input.send_keys("newuser")
        password_input = self.chrome.find_element_by_name("password")
        password_input.send_keys("password123")
        self.chrome.find_element_by_xpath("//button[@type='submit']").click()

        link = self.chrome.find_element_by_link_text("Click Here to Create New Condo")

        self.chrome.find_element_by_xpath("//a[@id='create-condo-link']").click()

        first_field_label = self.chrome.find_element_by_xpath("//label[@for='id_name']")
        self.assertIn("Condo Name", first_field_label.text)

        name_input = self.chrome.find_element_by_xpath("//input[@id='id_name']")
        name_input.send_keys(self.condo_data["name"])

        self.chrome.find_element_by_xpath("//input[@type='submit']").click()

        condos = Condo.objects.all()
        condo = Condo.objects.get(name=self.condo_data["name"])

        self.assertTrue(condos.exists())
        self.assertTrue(condo.name == self.condo_data["name"])

@tag("selenium")
@override_settings(
    DEBUG=True,
)
class AddNewBankAccountandInvestmentsTests(BaseTestCase):
    fixtures = ["users.json"]

    def setUp(cls):
        cls.condo_data = {
                        "name": "Toronto Standard Condominium Corporation 1978",
        }
        cls.condo = Condo.objects.create(**cls.condo_data)
        cls.condo = Condo.objects.get(id=cls.condo.id)

    def test_add_new_bank_account_and_add_new_investments(self):
        self.chrome.get("{}".format(self.live_server_url) + "/login/")
        username_input = self.chrome.find_element_by_name("username")
        username_input.send_keys("newuser")
        password_input = self.chrome.find_element_by_name("password")
        password_input.send_keys("password123")
        self.chrome.find_element_by_xpath("//button[@type='submit']").click()

        self.chrome.find_element_by_link_text(self.condo_data["name"]).click()

        body = self.chrome.find_element_by_xpath("//body")
        self.assertIn("Click Here to Add a Bank Account", body.text)
        self.assertIn("Click Here to Add Investments to your portfolio", body.text)

        self.chrome.find_element_by_link_text("Click Here to Add a Bank Account").click()

        body = self.chrome.find_element_by_xpath("//body")
        self.assertIn("Account Number", body.text)

        number_input = self.chrome.find_element_by_xpath("//input[@name='account_number']")
        number_input.send_keys("JZ12-416")

        institution_input = self.chrome.find_element_by_xpath("//input[@name='institution']")
        institution_input.send_keys("CIBC")

        type_input = self.chrome.find_element_by_xpath("//select[@name='type']")
        type_input.send_keys("Reserve")

        self.chrome.find_element_by_xpath("//input[@type='submit']").click()

        accounts = BankAccounts.objects.all()
        for account in accounts:
            account_id = account.pk
        account = BankAccounts.objects.get(id=account_id)

        self.assertTrue(accounts.exists())
        self.assertTrue(account.condo == self.condo)
        self.assertTrue(account.account_number == "JZ12-416")
        self.assertTrue(account.institution == "CIBC")
        self.assertTrue(account.type == "RESERVE")

        body = self.chrome.find_element_by_xpath("//body")
        self.assertIn("These are your account details", body.text)
        self.assertIn("Click Here to Add your current Bank Account Balance", body.text)

        self.chrome.find_element_by_link_text("Click Here to Add Investments to your portfolio").click()

        body = self.chrome.find_element_by_xpath("//body")
        self.assertIn("Instrument Number", body.text)

        number_input = self.chrome.find_element_by_xpath("//input[@name='instrument_number']")
        number_input.send_keys("Bz1832MD")

        institution_input = self.chrome.find_element_by_xpath("//input[@name='institution']")
        institution_input.send_keys("CIBC")

        amount_input = self.chrome.find_element_by_xpath("//input[@name='amount']")
        amount_input.send_keys("100000")

        rate_input = self.chrome.find_element_by_xpath("//input[@name='interest_rate']")
        rate_input.send_keys("0.04")

        maturity_input = self.chrome.find_element_by_xpath("//input[@name='maturity_date']")
        maturity_input.send_keys("21-12-2023")

        freq_input = self.chrome.find_element_by_xpath("//select[@name='interest_frequency']")
        freq_input.send_keys("ANNUAL")
        self.chrome.find_element_by_xpath("//input[@type='submit']").click()

        body = self.chrome.find_element_by_xpath("//body")
        self.assertIn("These are your account details", body.text)
        self.assertIn("Click Here to Add your current Bank Account Balance", body.text)

        self.assertIn("Current Investment Portfolio", body.text)
        self.assertIn("You currently do not have an investment plan", body.text)
        self.assertIn("Click Here to Add More Investments to your portfolio", body.text)

        self.chrome.find_element_by_link_text("Click Here to Add More Investments to your portfolio").click()

        body = self.chrome.find_element_by_xpath("//body")
        self.assertIn("Instrument Number", body.text)

        number_input = self.chrome.find_element_by_xpath("//input[@name='instrument_number']")
        number_input.send_keys("Bz1832MDcccd2")

        institution_input = self.chrome.find_element_by_xpath("//input[@name='institution']")
        institution_input.send_keys("CIBC")

        amount_input = self.chrome.find_element_by_xpath("//input[@name='amount']")
        amount_input.send_keys("125000")

        rate_input = self.chrome.find_element_by_xpath("//input[@name='interest_rate']")
        rate_input.send_keys("0.035")

        maturity_input = self.chrome.find_element_by_xpath("//input[@name='maturity_date']")
        maturity_input.send_keys("21-12-2023")

        freq_input = self.chrome.find_element_by_xpath("//select[@name='interest_frequency']")
        freq_input.send_keys("QUARTERLY")
        self.chrome.find_element_by_xpath("//input[@type='submit']").click()

        body = self.chrome.find_element_by_xpath("//body")
        self.assertIn("These are your account details", body.text)
        self.assertIn("Click Here to Add your current Bank Account Balance", body.text)

        self.assertIn("Current Investment Portfolio", body.text)
        self.assertIn("Bz1832MDcccd2", body.text)
        self.assertIn("CIBC", body.text)
        self.assertIn("You currently do not have an investment plan", body.text)
        self.assertIn("You currently have not uploaded an reserve fund study", body.text)
        self.assertIn("Click Here to Add More Investments to your portfolio", body.text)

        self.chrome.find_element_by_link_text("Click Here to Add your current Bank Account Balance").click()

        body = self.chrome.find_element_by_xpath("//body")
        self.assertIn("Reserve Balance", body.text)

        balance_input = self.chrome.find_element_by_xpath("//input[@name='balance']")
        balance_input.send_keys("125123")

        date_input = self.chrome.find_element_by_xpath("//input[@name='date']")
        date_input.send_keys("14-05-2018")

        self.chrome.find_element_by_xpath("//input[@type='submit']").click()

        body = self.chrome.find_element_by_xpath("//body")
        self.assertIn("These are your account details", body.text)
        self.assertIn("Click Here to Update your Bank Account Balance", body.text)
        self.assertIn("125123", body.text)
        self.assertIn("Reserve Fund Bank Account", body.text)
        self.assertIn("Current Investment Portfolio", body.text)
        self.assertIn("Bz1832MDcccd2", body.text)
        self.assertIn("CIBC", body.text)
        self.assertIn("You currently do not have an investment plan", body.text)
        self.assertIn("You currently have not uploaded an reserve fund study", body.text)
        self.assertIn("Click Here to Add More Investments to your portfolio", body.text)
