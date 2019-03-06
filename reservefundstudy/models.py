from datetime import datetime as dt

from django.utils import timezone

from django.db import transaction
from django.db.models import Model, CharField, DateField, DateTimeField, FileField, DecimalField, \
                            FloatField, IntegerField, PositiveSmallIntegerField, ForeignKey, \
                            OneToOneField, BooleanField, CASCADE, PROTECT
from condo.helpers import condo_short_name

from robocondo.global_helpers import RoCoManager


YEAR_CHOICES = [(r,r) for r in range(2010, (dt.now().year+31))]
MAX_STUDY_LENGTH = 30

class Study(Model):

    objects = RoCoManager()

    condo = ForeignKey("condo.Condo", on_delete=CASCADE)
    date = DateField("Date of Reserve Fund Study")
    current = BooleanField("Current", default=False)
    first_year = IntegerField("First Year of Study", choices=YEAR_CHOICES, default=timezone.now().year)
    last_year = IntegerField("Last Year of Study", choices=YEAR_CHOICES, default=(timezone.now().year + MAX_STUDY_LENGTH))
    years = IntegerField("Number of Years in Study", default=0)
    opening_balance = FloatField("Opening Balance", default=0)
    date_added = DateTimeField("Date and Time Added", editable=False, auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)
    archived = BooleanField("Archived", default=False)

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            self.date_added = timezone.now()
        if self.pk:
            self.date_modified = timezone.now()
        super().save(*args, **kwargs)

        if self.current == True:
            Study.objects.exclude(id=self.pk).filter(condo=self.condo).update(current=False)

    def __str__(self):
        return "{} - {} - {}".format("RFS", condo_short_name(self.condo.name), self.date)

class Contributions(Model):
    study = OneToOneField("Study", on_delete=CASCADE)
    cont_year_1 = FloatField("Year 1", null=True)
    cont_year_2 = FloatField("Year 2", null=True)
    cont_year_3 = FloatField("Year 3", null=True)
    cont_year_4 = FloatField("Year 4", null=True)
    cont_year_5 = FloatField("Year 5", null=True)
    cont_year_6 = FloatField("Year 6", null=True)
    cont_year_7 = FloatField("Year 7", null=True)
    cont_year_8 = FloatField("Year 8", null=True)
    cont_year_9 = FloatField("Year 9", null=True)
    cont_year_10 = FloatField("Year 10", null=True)
    cont_year_11 = FloatField("Year 11", null=True)
    cont_year_12 = FloatField("Year 12", null=True)
    cont_year_13 = FloatField("Year 13", null=True)
    cont_year_14 = FloatField("Year 14", null=True)
    cont_year_15 = FloatField("Year 15", null=True)
    cont_year_16 = FloatField("Year 16", null=True)
    cont_year_17 = FloatField("Year 17", null=True)
    cont_year_18 = FloatField("Year 18", null=True)
    cont_year_19 = FloatField("Year 19", null=True)
    cont_year_20 = FloatField("Year 20", null=True)
    cont_year_21 = FloatField("Year 21", null=True)
    cont_year_22 = FloatField("Year 22", null=True)
    cont_year_23 = FloatField("Year 23", null=True)
    cont_year_24 = FloatField("Year 24", null=True)
    cont_year_25 = FloatField("Year 25", null=True)
    cont_year_26 = FloatField("Year 26", null=True)
    cont_year_27 = FloatField("Year 27", null=True)
    cont_year_28 = FloatField("Year 28", null=True)
    cont_year_29 = FloatField("Year 29", null=True)
    cont_year_30 = FloatField("Year 30", null=True)

    def __str__(self):
        return "Condo {} RFS {}: Conts".format(condo_short_name(self.study.condo.name), self.study.date)

class Expenditures(Model):
    study = OneToOneField("Study", on_delete=CASCADE)
    exp_year_1 = FloatField("Year 1", null=True)
    exp_year_2 = FloatField("Year 2", null=True)
    exp_year_3 = FloatField("Year 3", null=True)
    exp_year_4 = FloatField("Year 4", null=True)
    exp_year_5 = FloatField("Year 5", null=True)
    exp_year_6 = FloatField("Year 6", null=True)
    exp_year_7 = FloatField("Year 7", null=True)
    exp_year_8 = FloatField("Year 8", null=True)
    exp_year_9 = FloatField("Year 9", null=True)
    exp_year_10 = FloatField("Year 10", null=True)
    exp_year_11 = FloatField("Year 11", null=True)
    exp_year_12 = FloatField("Year 12", null=True)
    exp_year_13 = FloatField("Year 13", null=True)
    exp_year_14 = FloatField("Year 14", null=True)
    exp_year_15 = FloatField("Year 15", null=True)
    exp_year_16 = FloatField("Year 16", null=True)
    exp_year_17 = FloatField("Year 17", null=True)
    exp_year_18 = FloatField("Year 18", null=True)
    exp_year_19 = FloatField("Year 19", null=True)
    exp_year_20 = FloatField("Year 20", null=True)
    exp_year_21 = FloatField("Year 21", null=True)
    exp_year_22 = FloatField("Year 22", null=True)
    exp_year_23 = FloatField("Year 23", null=True)
    exp_year_24 = FloatField("Year 24", null=True)
    exp_year_25 = FloatField("Year 25", null=True)
    exp_year_26 = FloatField("Year 26", null=True)
    exp_year_27 = FloatField("Year 27", null=True)
    exp_year_28 = FloatField("Year 28", null=True)
    exp_year_29 = FloatField("Year 29", null=True)
    exp_year_30 = FloatField("Year 30", null=True)

    def __str__(self):
        return "Condo {} RFS {}: Exps".format(condo_short_name(self.study.condo.name), self.study.date)
