from datetime import datetime as dt, date

from django.test import TestCase
from django.utils import timezone

from condo.models import Condo, BankAccounts, AccountBalance, Investments
from condo.forms import BankAccountsForm, AccountBalanceForm, InvestmentsForm

class BankAccountsFormTests(TestCase):

    def test_bank_accounts_form_is_valid(self):
        account_data = {
                        "account_number": "JZ12-416",
                        "institution": "CIBC", "type": "RESERVE",
        }
        form = BankAccountsForm(account_data)
        self.assertTrue(form.is_valid())

    def test_account_type_choices_doesnt_allow_invalid_choice(self):
        account_data = {
                        "account_number": "JZ12-416",
                        "institution": "CIBC", "type": "not a choice",
        }
        form = BankAccountsForm(account_data)
        self.assertFalse(form.is_valid())
        self.assertIn("not one of the available choices", form.errors["type"][0])

class AccountBalanceFormTests(TestCase):

    def test_account_balance_form_is_valid(self):
        balance_data = {
                        "balance": 105000, "date": "14-05-2018"
        }
        form = AccountBalanceForm(balance_data)
        self.assertTrue(form.is_valid())

    def test_balance_cannot_be_negative(self):
        balance_data = {
                        "balance": -105000, "date": "14-05-2018"
        }
        form = AccountBalanceForm(balance_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Ensure this value is greater than or equal to 0", form.errors["balance"][0])

class InvestmentsFormTests(TestCase):

    def test_invmts_form_is_valid(self):
        invmts_data = {
                        "instrument_number": "Bz1832MD", "institution": "CIBC",
                        "amount": 100000, "interest_rate": 0.04, "maturity_date": "21-12-2023",
                        "interest_frequency": "ANNUAL"
        }
        form = InvestmentsForm(invmts_data)
        print (form.errors)
        self.assertTrue(form.is_valid())

    def test_amount_cannot_be_negative(self):
        invmts_data = {
                        "instrument_number": "Bz1832MD", "institution": "CIBC",
                        "amount": -100000, "interest_rate": -0.04, "maturity_date": "21-12-2023",
                        "interest_frequency": "ANNUAL"
        }
        form = InvestmentsForm(invmts_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Ensure this value is greater than or equal to 0", form.errors["amount"][0])
        self.assertIn("Ensure this value is greater than or equal to 0", form.errors["interest_rate"][0])

    def test_interest_frequency_must_be_a_valid_choice(self):
        invmts_data = {
                        "instrument_number": "Bz1832MD", "institution": "CIBC",
                        "amount": 100000, "interest_rate": 0.04, "maturity_date": "21-12-2023",
                        "interest_frequency": "not a choice"
        }
        form = InvestmentsForm(invmts_data)
        self.assertFalse(form.is_valid())
        self.assertIn("not one of the available choices", form.errors["interest_frequency"][0])
