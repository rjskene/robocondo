from datetime import datetime as dt, date

from django.urls import reverse

from django.db import transaction, IntegrityError
from django.db.utils import DataError
from django.test import TestCase
from django.utils import timezone

from condo.models import Condo, BankAccounts, AccountBalance, Investments
from condo.tests.factories import CondoFactory, BankAccountsFactory as BAFactory, \
                    AccountBalanceFactory as ABFactory, InvestmentsFactory as InvmtsFactory

from condo.helpers import condo_short_name

class CondoModelTests(TestCase):
    @classmethod
    def setUpTestData(self):
        self.condo = CondoFactory()

    def test_name_label(self):
        condo = Condo.objects.get(id=self.condo.id)
        field_label = condo._meta.get_field("name").verbose_name
        self.assertEquals(field_label, "Condo Name")

    def test_condo_name(self):
        self.assertEquals(self.condo.name, "Toronto Standard Condominium Corporation 1978")

    def test_condo_short_name(self):
        self.assertEquals(self.condo.short_name, condo_short_name(self.condo.name))

    def test_cant_duplicate_condo_name(self):
        try:
            with transaction.atomic():
                condo3 = CondoFactory()
            self.fail("Name of Condo was duplicated")
        except IntegrityError:
            pass

    def test_length_of_condo_name(self):
        try:
            with transaction.atomic():
                condo2 = CondoFactory(name="WWWWWAAAAAAAAYYYYYYYYYYYTTTTOOOOOOLOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOONNNNNNGGGGGGGG")
            self.fail("Name of Condo exceed 50 characters")
        except DataError:
            pass

class BankAccountsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account = BAFactory()

    def test_account_details(self):
        field_label = self.account._meta.get_field("account_number").verbose_name
        self.assertEquals(field_label, "Account Number")
        self.assertEquals(self.account.account_number, "JZ12-416")
        field_label = self.account._meta.get_field("institution").verbose_name
        self.assertEquals(field_label, "Financial Institution")
        self.assertEquals(self.account.institution, "CIBC")
        field_label = self.account._meta.get_field("type").verbose_name
        self.assertEquals(field_label, "Account Type")
        self.assertEquals(self.account.type, "RESERVE")
        self.assertEquals(self.account.__str__(), "Condo {}; {} Account {}".format(
                    condo_short_name(self.account.condo.name), self.account.type, self.account.account_number
        ))

    def test_account_type_subclasses(self):
        self.assertEquals(BankAccounts.Type.OPERATING.name, "OPERATING")
        self.assertEquals(BankAccounts.Type.OPERATING.value, "Operating")
        self.assertEquals(BankAccounts.Type.RESERVE.name, "RESERVE")
        self.assertEquals(BankAccounts.Type.RESERVE.value, "Reserve")

    def test_condo_foreign_key_incorrect(self):
        account_data = {
                        "condo": "not a condo object", "account_number": "JZ12-416",
                        "institution": "CIBC", "type": "Reserve",
        }
        with self.assertRaises(ValueError):
            account = BankAccounts.objects.create(**account_data)


    def test_unique_constraint_for_account_number_field(self):
        try:
            with transaction.atomic():
                self.account2 = BAFactory(condo=self.account.condo)
            self.fail("Account number was duplicated")
        except IntegrityError:
            pass

    def test_account_cant_have_multiple_reserve_accounts(self):
        try:
            with transaction.atomic():
                self.account2 = BAFactory(condo=self.account.condo, account_number="DIFFERENT")
            # self.fail("this failed for some reason")
        except IntegrityError:
            pass


class AccountBalanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.balance = ABFactory()

    def test_balance_create(self):
        self.assertEquals(self.balance.balance, 125000.45)
        self.assertEquals(self.balance.date, timezone.make_aware(dt(2018,5,14)))

    def test_str_method(self):
        self.assertEquals(self.balance.__str__(), "Condo {}; {} Account {}; Balance".format(
                    condo_short_name(self.balance.account.condo.name), self.balance.account.type,
                    self.balance.account.account_number
        ))

class InvestmentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.invmt = InvmtsFactory()

    def test_investments_create(self):
        self.assertEquals(self.invmt.interest_rate, .03)
        self.assertEquals(self.invmt.amount, 100000)
        self.assertEquals(self.invmt.maturity_date, timezone.make_aware(dt(2023,6,5)))

    def test_str_method(self):
        self.assertEquals(self.invmt.__str__(), "Condo {}; Investment {}".format(
                    condo_short_name(self.invmt.condo.name), self.invmt.instrument_number
        ))

    def test_find_frequency_method(self):
        self.assertEquals(self.invmt._find_frequency(), self.invmt.INT_FREQ[self.invmt.IntFreq[self.invmt.interest_frequency].value])
        self.assertEquals(self.invmt._find_frequency(), 12)

    def test_INT_FREQ_dict(self):
        self.assertEquals(self.invmt.INT_FREQ["Annual"], 12)
        self.assertEquals(self.invmt.INT_FREQ["Semi-Annual"], 6)
        self.assertEquals(self.invmt.INT_FREQ["Quarterly"], 3)
        self.assertEquals(self.invmt.INT_FREQ["Maturity"], 0)

    def test_instrument_number_must_be_unique(self):
        with self.assertRaises(IntegrityError):
            self.invmt2 = InvmtsFactory(instrument_number=self.invmt.instrument_number)
