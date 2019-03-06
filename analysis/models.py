from django.db.models import Model, Manager, CharField, DateField, DateTimeField, FileField, DecimalField, \
                            FloatField, IntegerField, PositiveSmallIntegerField, ForeignKey, \
                            OneToOneField, CASCADE, PROTECT, BooleanField

class Analysis(Model):

    condo = ForeignKey("condo.Condo", on_delete=PROTECT)
    study = ForeignKey("reservefundstudy.Study", on_delete=PROTECT)
    forecast = ForeignKey("pyyc.Forecast", on_delete=PROTECT)

class ForecastManager(Manager):
    def bulk_create(self, objs, group, dates, batch_size=None):
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
                objs[idx].group = group
                objs[idx].month = dates[idx]
            objs = iter(objs)

            return super().bulk_create(objs, batch_size=None)
        else:
            raise ValueError(
                    """
                    The length of the dates array does not match the number of periods
                    in Pyondo model output
                    """
            )

class Forecast(Model):
    objects = ForecastManager()

    group = PositiveSmallIntegerField("Forecast Group")
    period = IntegerField("Period")
    month = DateTimeField("Month")
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
        unique_together = ("group", "period", "month")

    def __str__(self):
        return "Forecast {}; Period {}".format(
                    self.group, self.period
        )
