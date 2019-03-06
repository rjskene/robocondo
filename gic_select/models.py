from django.db import transaction
from django.db.models import Manager, Model, BooleanField, CharField, DateField, DateTimeField, FileField, DecimalField, \
                            FloatField, IntegerField, PositiveSmallIntegerField, ForeignKey, \
                            OneToOneField, CASCADE, PROTECT
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone

from robocondo.global_helpers import ChoiceEnum

class GICManager(Manager):
    def latest_gics(self):
        last_date = GICs.objects.latest("date").date
        return GICs.objects.filter(date=last_date)

class GICs(Model):
    objects = GICManager()

    date = DateField("Date")
    issuer = CharField("Issuer", max_length=30)
    amount = IntegerField("Amount")
    term = PositiveSmallIntegerField("Term of GIC", validators=[MinValueValidator(1), MaxValueValidator(5)])
    rate = FloatField("Rate")

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    class Meta:
        unique_together = ("date", "issuer", "amount", "term")

    def __str__(self):
        return "GIC: Issuer {}; Term {}; Date {}".format(self.issuer, self.term, self.date)

class GICPlan(Model):
    """
    GICPlan model logs details of the particular GIC Forecast including which Investment Plan it is related to,
    when it was added, and whether it is the Current or Archived Plan.
    There is only ONE record designated Current and all other records are designated ARCHIVED
    by modifying the .save() method
    The actual GICs outlined in the plan are detailed in GICSelect
    """

    class Status(ChoiceEnum):
        CURRENT = "Current"
        ARCHIVED = "Archived"

    plan = ForeignKey("investmentplan.Plan", on_delete=CASCADE)
    date = DateField("Date")
    status_bool = BooleanField("Current/Default Boolean", default=False)
    status = CharField("Current/Archived", choices=Status.choices(), max_length=9)
    date_added = DateTimeField("Date and Time Added", editable=False)
    date_modified = DateTimeField("Date and Time Modified")

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Set status_bool and status attribute to True and Current if this is the most recent
        plan added to the db
        If the plan being added is the most current, adjust all prior entries to False and ARCHIVED
        Must set date_added / date_modified manually so that they are available for logical comparison
        """
        if not self.pk:
            self.date_added = timezone.now()

        self.date_modified = timezone.now()

        if GICPlan.objects.all():
            print (self.date_added, GICPlan.objects.latest("date_added").date_added)
            self.status_bool = self.date_added > GICPlan.objects.latest("date_added").date_added
        else:
            self.status_bool = True

        self.status = self.Status.CURRENT.value if self.status_bool else self.Status.ARCHIVED.value

        if self.status_bool:
            try:
                GICPlan.objects.filter(
                    date_added__lt=self.date_added).update(status_bool=False)
                GICPlan.objects.filter(
                    date_added__lt=self.date_added).update(status=self.Status.ARCHIVED.value)
            except GICPlan.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} {}; Condo {}; Investment Plan {}".format(
                    self.status, "GICPlan",
                    self.plan.study.condo.name, self.plan
        )

class GICSelect(Model):
    gic_plan = ForeignKey("GICPlan", on_delete=CASCADE)
    gic = ForeignKey("GICs", on_delete=CASCADE)
    amount = FloatField("Investment Amount")

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def __str__(self):
        return "{} ; Plan: {}; Amount {}".format(
                self.gic_plan, self.gic, self.amount
        )

class CDIC(Model):
    name = CharField("Name of Insured Instituion", max_length=100)

class DICO(Model):
    name = CharField("Name of Insured Instituion", max_length=400)
