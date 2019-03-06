from datetime import datetime as dt

from factory.django import DjangoModelFactory
from factory import SubFactory, Sequence

from django.utils import timezone

from condo.models import Condo, BankAccounts, AccountBalance, Investments

class CondoFactory(DjangoModelFactory):

    class Meta:
        model = Condo

    name = "Toronto Standard Condominium Corporation 1978"

class CondoDupFactory(CondoFactory):
    class Meta:
        django_get_or_create = ("name", )

class BankAccountsFactory(DjangoModelFactory):
    class Meta:
        model = BankAccounts
        django_get_or_create = ("condo", )

    condo = SubFactory(CondoFactory)
    account_number = "JZ12-416"
    institution = "CIBC"
    type =  "Reserve"
    spread = 0.03

class AccountBalanceFactory(DjangoModelFactory):
    class Meta:
        model = AccountBalance
        django_get_or_create = ("account", )

    account = SubFactory(BankAccountsFactory)
    balance = 125000
    date = timezone.make_aware(dt(2012,5,14))

class InvestmentsFactory(DjangoModelFactory):
    class Meta:
        model = Investments

    condo = SubFactory(CondoFactory)
    instrument_number = Sequence(lambda n: "912398-11{}".format(n))
    institution = "CIBC"
    amount = 100000
    interest_rate = .03
    maturity_date = timezone.make_aware(dt(2023,6,5))
    interest_frequency = "ANNUAL"

class InvestmentsDupFactory(InvestmentsFactory):
    class Meta:
        django_get_or_create = ("condo", )
