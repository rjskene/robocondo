from datetime import date

from django.db import models
from django.db.models import Model, CharField, DateField, DateTimeField, FileField, DecimalField, \
                            FloatField, IntegerField, PositiveSmallIntegerField, ForeignKey, \
                            OneToOneField, CASCADE, PROTECT, BooleanField
from django.core.validators import MinValueValidator

from robocondo.global_helpers import ChoiceEnum, valid_pct, RoCoManager

from .helpers import condo_short_name

class Condo(Model):
    name = CharField("Condo Name", max_length=100, unique=True)
    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    @property
    def short_name(self):
        return condo_short_name(self.name)

    def __str__(self):
        return "{}".format(condo_short_name(self.name))

class AccountsManager(RoCoManager):
    def filter_archived(self, **kwargs):
        return self.filter_or_none(**kwargs, archived=False)

class BankAccounts(Model):

    objects = AccountsManager()

    class Type(ChoiceEnum):
        OPERATING = "Operating"
        RESERVE = "Reserve"

    condo = ForeignKey("Condo", on_delete=CASCADE)
    account_number = CharField("Account Number", max_length=50, unique=True)
    institution = CharField("Financial Institution", max_length=400)
    type = CharField("Account Type", choices=Type.choices(), max_length=20)
    spread = FloatField("Spread Below Prime Rate")
    archived = BooleanField("Archived", default=False)
    date_added = DateTimeField("Date and Time Added", editable=False, auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def __str__(self):
        return "Condo {}; {} Account {}".format(
                    condo_short_name(self.condo.name), self.type, self.account_number
        )

    class Meta:
        unique_together = (("account_number", "institution"),)

class AccountBalance(Model):

    objects = RoCoManager()

    account = ForeignKey("BankAccounts", on_delete=CASCADE)
    balance = FloatField("Reserve Balance", validators=[MinValueValidator(0)])
    date = DateTimeField("Date")
    date_added = DateTimeField("Date and Time Added", editable=False, auto_now_add=True)

    def __str__(self):
        return "Condo {}; {} Account {}; Balance".format(
                    condo_short_name(self.account.condo.name), self.account.type, self.account.account_number
        )

class InvmtManager(RoCoManager):
    def current(self, **kwargs):
        return self.filter_or_none(**kwargs, archived=False, maturity_date__gte=date.today())

class Investments(Model):

    INT_FREQ = {
        "Annual": 12,
        "Semi-Annual": 6,
        "Quarterly": 3,
        "Maturity": 0
    }

    class IntFreq(ChoiceEnum):
        ANNUAL = "Annual"
        SEMI_ANNUAL = "Semi-Annual"
        QUARTERLY = "Quarterly"
        MATURITY = "Maturity"

    objects = InvmtManager()

    condo = ForeignKey("Condo", on_delete=CASCADE)
    instrument_number = CharField("Instrument Number", unique=True, blank=True, max_length=30)
    institution = CharField("Financial Institution", max_length=100)
    amount = FloatField("Amount", validators=[MinValueValidator(0)])
    interest_rate = FloatField("Interest Rate", validators=[MinValueValidator(0)], max_length=10)
    maturity_date = DateTimeField("Maturity Date")
    interest_frequency = CharField("Interest Frequency", choices=IntFreq.choices(), max_length=20)
    archived = BooleanField("Archived", default=False)
    date_added = DateTimeField("Date and Time Added", editable=False, auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def _find_frequency(self):
        return self.INT_FREQ[self.IntFreq[self.interest_frequency].value]

    def __str__(self):
        return "Condo {}; Investment {}".format(
                    condo_short_name(self.condo.name), self.instrument_number
        )
