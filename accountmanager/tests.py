import time
import socket
from datetime import datetime as dt

from django.urls import reverse

from django.test import TestCase, tag, LiveServerTestCase
from django.test.client import Client
from django.contrib.auth.models import User

from decouple import config

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

@tag('selenium')
class BaseTestCase(LiveServerTestCase):
    """
    Extends StaticLiveServerTestCase so that it works with Selenium hub
    and the various Docker containers
    """

    host = '0.0.0.0'  # Bind to 0.0.0.0 to allow external access

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Set host to externally accessible web server address
        cls.host = socket.gethostbyname(socket.gethostname())

        # Instantiate the remote WebDriver
        cls.chrome = webdriver.Remote(
            command_executor='http://selenium_hub:4444/wd/hub',
            desired_capabilities=DesiredCapabilities.CHROME,
        )
        cls.chrome.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.chrome.quit()
        super().tearDownClass()

@tag('selenium')
class AccountManagerTests(BaseTestCase):
    fixtures = ['users.json']

    def test_signup(self):
        self.chrome.get('{}'.format(self.live_server_url) + '/signup/')
        username_input = self.chrome.find_element_by_name('username')
        username_input.send_keys('newuser2')
        firstname_input = self.chrome.find_element_by_name('first_name')
        firstname_input.send_keys('New2')
        lastname_input = self.chrome.find_element_by_name('last_name')
        lastname_input.send_keys('User2')
        email_input = self.chrome.find_element_by_name('email')
        email_input.send_keys('new.user2@domain.com')
        password_input = self.chrome.find_element_by_name('password1')
        password_input.send_keys('password123')
        confirmation_input = self.chrome.find_element_by_name('password2')
        confirmation_input.send_keys('password123')
        self.chrome.find_element_by_xpath("//button[@type='submit']").click()

        body = self.chrome.find_element_by_xpath('//body')
        self.assertIn('dashboard', body.text)

    def test_login_and_logout(self):
        self.chrome.get('{}'.format(self.live_server_url) + '/login/')
        username_input = self.chrome.find_element_by_name('username')
        username_input.send_keys('newuser')
        password_input = self.chrome.find_element_by_name('password')
        password_input.send_keys('password123')
        self.chrome.find_element_by_xpath("//button[@type='submit']").click()

        # Check if dashboard is in the HTML
        body = self.chrome.find_element_by_xpath('//body')
        self.assertIn('This is the User dashboard', body.text)

        # Logout
        self.chrome.find_element_by_id('navbar-logout').click()

class TestsUsingDjangoClient(TestCase):
    fixtures = ['users.json']

    def setUp(self):
        self.client = Client()

    def test_login_and_logout_results_for_authenticated_user_or_anonymous_user(self):
        response = self.client.post(
                                        reverse('accountmanager:login'),
                                        {
                                            'username': 'newuser',
                                            'password': 'password123',
                                         }
                                    )
        self.assertEquals(response.wsgi_request.user.username, 'newuser')


        self.client.logout()
        response = self.client.get('/admin/')

        # AnonymousUser has empty string for username attribute


        self.assertEquals(response.wsgi_request.user.username, '')

class SiteVists(BaseTestCase):

    def test_visit_site_with_chrome(self):
        self.chrome.get("{}".format(self.live_server_url))
        self.assertIn(self.chrome.title, "RoboCondo: Investing for Condominiums Made Easy")

    def test_visit_signup_with_chrome(self):
        self.chrome.get("{}".format(self.live_server_url) + "/signup/")
        title = self.chrome.find_element_by_xpath('//h2')
        self.assertIn(title.text, "Sign up")

    def test_visit_login_with_chrome(self):
        self.chrome.get("{}".format(self.live_server_url) + "/login/")
        title = self.chrome.find_element_by_xpath('//h2')
        self.assertIn(title.text, "Login")

class AdminTests(BaseTestCase):
    fixtures = ['user.json']

    def test_login_and_logout(self):
        self.chrome.get("{}".format(self.live_server_url) + "/admin/login/")
        username_input = self.chrome.find_element_by_name("username")
        username_input.send_keys('admin')
        password_input = self.chrome.find_element_by_name("password")
        password_input.send_keys(config('ADMIN_PASSWORD'))
        self.chrome.find_element_by_xpath('//input[@value="Log in"]').click()
        self.assertIn(self.chrome.title, "Site administration | Django site admin")

        self.chrome.find_element_by_xpath('//a[@href="/admin/logout/"]').click()
        self.assertIn(self.chrome.title, "Logged out | Django site admin")
