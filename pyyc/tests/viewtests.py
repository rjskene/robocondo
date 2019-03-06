import time
import socket
from datetime import datetime as dt, date
from dateutil.relativedelta import relativedelta
import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np
from unittest.mock import patch
from urllib.request import urlopen, Request, urlretrieve
from bs4 import BeautifulSoup as bs

import quandl

from django.db import transaction, IntegrityError
from django.forms.models import model_to_dict
from django.utils import timezone
from django.urls import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.test.client import Client
from django.contrib.auth.models import User
from django.test import TestCase, tag, LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from condo.models import Condo
from condo.helpers import condo_short_name

from pyondo.pyondo import Pyondo

from condo.models import Condo
from reservefundstudy.models import Study, Contributions, Expenditures
from investmentplan.models import Plan, Forecast
from investmentplan.helpers import int_to_date, find_date
from investmentplan.converter import Converter

from robocondo.global_helpers import get_or_none
from condo.tests.factories import CondoFactory, BankAccountsFactory as BAFactory, \
                    AccountBalanceFactory as ABFactory, InvestmentsFactory as InvmtsFactory
from investmentplan.tests.factories import PlanFactory
from reservefundstudy.tests.factories import StudyFactory, ContributionsFactory as ContFactory, \
            ExpendituresFactory as ExpFactory, cont_kwargs, exp_kwargs
from pyyc.models import HistoricalYieldCurve as HYC, HistoricalOvernightRate as HOR, \
                        InflationRate as INFR, OutputGap as GAP, RAW, \
                        PrincipalComponents as PC, Dataset, Cointegration as COINT, Technique as TECH, \
                        VAR, VARMA, VECM, Forecast
from pyyc.data.update import yc_upload, overnight_upload, inflation_upload, outputgap_upload, \
                        YC_PATH, IR_PATH, INF_PATH, GAP_PATH, historical_bulkcreate, \
                        create_techniques, make_values, update_gap, update_inf, update_bankrate, \
                        HYC_KEYS, update_data, update_bocgic
from pyyc.data.combine import make_combined_frame, make_frame
from pyyc.pyyc.analysis import PCA, CointAnal
from pyyc.pyyc.main import PYYC
from pyyc.pyyc.forecast import YieldCurveForecast, GICForecast

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
@override_settings(DEBUG=True)
class UpdateDataViewTest(BaseTestCase):
    fixtures = ["forecasts.json", "users.json"]

    def test_update_data(self):

        self.chrome.get("{}".format(self.live_server_url) + "/login/")
        username_input = self.chrome.find_element_by_name("username")
        username_input.send_keys("newuser")
        password_input = self.chrome.find_element_by_name("password")
        password_input.send_keys("password123")
        self.chrome.find_element_by_xpath("//button[@type='submit']").click()

        df_hor = pd.DataFrame(list(HOR.objects.all().values()))

        # Go to pyyc module
        self.chrome.find_element_by_id("navbar-pyyc").click()
        # Try to update data
        self.chrome.find_element_by_id("update-data-button").click()

        df_hor = pd.DataFrame(list(HOR.objects.all().values()))

    def test_run_forecasts(self):

        self.chrome.get("{}".format(self.live_server_url) + "/login/")
        username_input = self.chrome.find_element_by_name("username")
        username_input.send_keys("newuser")
        password_input = self.chrome.find_element_by_name("password")
        password_input.send_keys("password123")
        self.chrome.find_element_by_xpath("//button[@type='submit']").click()

        # Go to pyyc module
        self.chrome.find_element_by_id("navbar-pyyc").click()
        # Try to update data
        self.chrome.find_element_by_id("run-forecasts-button").click()
