from datetime import datetime as dt
from dateutil.relativedelta import relativedelta

from django.db.models import Manager, Model, BooleanField, CharField, DateField, DateTimeField, FileField, DecimalField, \
                            FloatField, IntegerField, PositiveSmallIntegerField, ForeignKey, \
                            OneToOneField, CASCADE, PROTECT
from django.db import transaction
from django.utils import timezone

from .helpers import find_date

from robocondo.global_helpers import ChoiceEnum, RoCoManager
from condo.helpers import condo_short_name
from reservefundstudy.models import Study

class Plan(Model):
    """
    Investment Plan model logs details of the Plan including which study it is related to,
    when it was added, and whether it is the Current or Archived Plan
    There is only ONE record designated Current and all other records are designated ARCHIVED
    by modifying the .save() method
    """

    objects = RoCoManager()

    class Status(ChoiceEnum):
        CURRENT = "Current"
        ARCHIVED = "Archived"

    study = ForeignKey("reservefundstudy.Study", on_delete=PROTECT)
    status_bool = BooleanField("Current/Default Boolean", default=False)
    status = CharField("Current/Archived", choices=Status.choices(), max_length=9)
    time = FloatField("Time to Complete", default=0)
    date_added = DateTimeField("Date and Time Added", editable=False)
    date_modified = DateTimeField("Date and Time Modified")

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Set status_bool and status attribute to True and Current if this is the most recent
        plan added to the db
        If the plan being added is the most current, adjust all prior entries to False and ARCHIVED
        Only one current PER CONDO
        Must set date_added / date_modified manually so that they are available for logical comparison
        """
        if not self.pk:
            self.date_added = timezone.now()
        self.date_modified = timezone.now()
        if Plan.objects.all():
            self.status_bool = self.date_added > Plan.objects.filter(study__condo=self.study.condo).latest("date_added").date_added
        else:
            self.status_bool = True

        self.status = self.Status.CURRENT.value if self.status_bool else self.Status.ARCHIVED.value

        if self.status_bool:
            try:
                Plan.objects.filter(
                    study__condo=self.study.condo,
                    date_added__lt=self.date_added).update(status_bool=False)
                Plan.objects.filter(
                    study__condo=self.study.condo,
                    date_added__lt=self.date_added).update(status=self.Status.ARCHIVED.value)
            except Plan.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} {}; Condo {}; Study {}".format(
                    self.status, "Plan",
                    condo_short_name(self.study.condo.name), self.study.date
        )

class ForecastManager(Manager):
    def bulk_create(self, objs, plan, dates, batch_size=None):
        """
        Modify bulk_create to update plan and month values from Pyondo output
        Add plan and dates args to inputs
        Set objs.plan to the specific plan instance
        Set objs.month to datetime adjusted for demo/non-demo nature of Plan instance.
        dates arg is list of dates from converter (which adjusts date range based
        on demo/non-demo selection for Plan).

        objs is a generator; must convert to list, edit, then convert back to generator
        """
        objs = list(objs)
        if len(objs) == len(dates):
            for idx, val in enumerate(objs):
                objs[idx].plan = plan
                objs[idx].month = dates[idx]
            objs = iter(objs)

            return super(ForecastManager, self).bulk_create(objs, batch_size=None)
        else:
            raise ValueError(
                    """
                    The length of the dates array does not match the number of periods
                    in Pyondo model output
                    """
            )

class Forecast(Model):
    objects = ForecastManager()

    plan = ForeignKey("Plan", on_delete=CASCADE)
    period = IntegerField("Period")
    month = DateTimeField("Month", default=timezone.make_aware(dt(1900,1,1)))
    opening_balance = FloatField("Opening Balance")
    contributions = FloatField("Contributions")
    expenditures = FloatField("Expenditures")
    interest = FloatField("Interest")
    closing_balance = FloatField("Closing Balance")
    bank_balance = FloatField("Bank Account Balance")
    current_investments = FloatField("Current Investments")
    maturities = FloatField("Maturities")

    term_1 = FloatField("Investment Term 1")
    term_2 = FloatField("Investment Term 2")
    term_3 = FloatField("Investment Term 3")
    term_4 = FloatField("Investment Term 4")
    term_5 = FloatField("Investment Term 5")

    total_investments = FloatField("Total Investments", default=0)

    class Meta:
        unique_together = ("plan", "period", "month")

    def __str__(self):
        return "{} Forecast; Plan: {}; Period {}".format(
                    self.plan.status,
                    self.plan.id, self.period
        )
