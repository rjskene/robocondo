import datetime
import pandas as pd

from django.db import models
from django.db import transaction, IntegrityError
from django.db.models import Model, Manager, CharField, DateField, DateTimeField, FileField, DecimalField, \
                            FloatField, IntegerField, PositiveSmallIntegerField, ForeignKey, \
                            OneToOneField, CASCADE, PROTECT, BooleanField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.postgres.fields import JSONField, ArrayField
from django.utils import timezone

from robocondo.global_helpers import ChoiceEnum, RoCoManager

def bool_string(boolean):
    if isinstance(boolean, bool):
        if boolean:
            return "T"
        else:
            return "F"
    else:
        raise TypeError("boolean must be of type bool")

class HistoricalYieldCurve(Model):
    date = DateField("Date", unique=True)

    three_month = FloatField("ZC025YR")
    six_month = FloatField("ZC050YR")
    one_year = FloatField("ZC100YR")
    two_year = FloatField("ZC200YR")
    three_year = FloatField("ZC300YR")
    four_year = FloatField("ZC400YR")
    five_year = FloatField("ZC500YR")
    seven_year = FloatField("ZC700YR")
    ten_year = FloatField("ZC1000YR")
    twenty_five_year = FloatField("ZC2500YR")

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def __str__(self):
        return "Historical YC Date {}".format(self.date)

class HistoricalOvernightRate(Model):
    date = DateField("Date", unique=True)
    rate = FloatField("Bank Rate")

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def __str__(self):
        return "Historical CAD Overnight Rate Date {}: {}".format(self.date, self.rate)

class InflationRate(Model):
    date = DateField("Date", unique=True)
    inflation = FloatField("Inflation")

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def __str__(self):
        return "Historical CPI Rate Date {}: {}".format(self.date, self.inflation)

class OutputGap(Model):
    date = DateField("Date", unique=True)
    output_gap = FloatField("Output Gap")

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def __str__(self):
        return "Output Gap Date {}: {}".format(self.date, self.output_gap)

class BOCGICs(Model):
    date = DateField("Date", unique=True)
    one_year = FloatField("1-Year GIC")
    three_year = FloatField("3-Year GIC")
    five_year = FloatField("5-Year GIC")
    prime = FloatField("Business Prime Rate")

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def __str__(self):
        return "Bank of Canada GICs Dated {}".format(self.date)

class ForecastManager(RoCoManager):
    def top_forecasts(self, n=None):
        top = Forecast.objects.latest_group()
        if n:
            sliced = top.order_by("total_rmse")[:n]
            return Forecast.objects.filter(id__in=sliced).order_by("total_rmse")
        else:
            return top.order_by("total_rmse")

    def latest_group(self):
        latest_group = Forecast.objects.latest("group")
        return Forecast.objects.filter(group=latest_group.group)

    def last_date(self):
        return Forecast.objects.latest_group()[0].dataset.end_date()

    def latest_forecasts(self):
        latest_datasets = Dataset.objects.latest_datasets()
        return Forecast.objects.filter(dataset__id__in=latest_datasets.values("id"))

class Forecast(Model):
    objects = ForecastManager()

    group = PositiveSmallIntegerField("Forecast Group", default=0)
    current = BooleanField("Current Forecast?", default=False)
    dataset = ForeignKey("Dataset", on_delete=PROTECT)
    technique = ForeignKey("Technique", on_delete=PROTECT)

    process_time = FloatField("Process Time")
    set_rmses = ArrayField(FloatField())
    total_rmse = FloatField("Total RMSE of Test")

    projected = JSONField("Projected Yield Curve")

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def __str__(self):
        return "{} {}".format(self.dataset, self.technique)

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            self.date_added = timezone.now()
        elif self.pk:
            if self.current == True:
                Forecast.objects.exclude(id=self.id).update(current=False)

        super().save(*args, **kwargs)

    def df(self):
        df = pd.read_json(self.projected, orient="index")
        df.index.name = "date"

        return df

class BOCGICForecast(Model):
    forecast = OneToOneField("Forecast", on_delete=PROTECT)
    json = JSONField("Projected GIC Curve")
    last_date = DateField("Last Date in Dataset")

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    @transaction.atomic
    def save(self, df, *args, **kwargs):
        df = df.copy()  # this allows multiple iterations of save() without alteration of df
        if not self.pk:
            self.date_added = timezone.now()
        self.date_modified = timezone.now()

        self.last_date = df.tail(1).index[0].to_pydatetime()
        self.json = df.to_json(orient="index")

        super().save(*args, **kwargs)

    def df(self):
        df = pd.read_json(self.json, orient="index")
        df.index.name = "Date"
        return df

    def split_rates(self, length=None):
        df = self.df()[["rate", "one_year", "two_year", "three_year", "four_year", "five_year"]]
        bank_rates = df[["rate"]].values.flatten()
        rates = df.drop("rate", axis=1).values

        if length:
            return bank_rates.tolist()[:length], rates.tolist()[:length]
        else:
            return bank_rates.tolist(), rates.tolist()

    def __str__(self):
        return "GIC Forecast for {} on Date {}".format(self.forecast, self.date_added)

class DatasetManager(RoCoManager):

    def latest_datasets(self):
        raw_date = Dataset.objects.filter(pc=None).latest("raw__last_date").raw.last_date
        raws = Dataset.objects.filter(pc=None, raw__last_date=raw_date)
        pc_date = Dataset.objects.filter(raw=None).latest("pc__raw__last_date").pc.raw.last_date
        pcs = Dataset.objects.filter(raw=None, pc__raw__last_date=pc_date)

        assert raw_date == pc_date

        return raws.union(pcs)

    def latest_last_date(self):
        raw_date = Dataset.objects.filter(pc=None).latest("raw__last_date").raw.last_date
        pc_date = Dataset.objects.filter(raw=None).latest("pc__raw__last_date").pc.raw.last_date

        assert raw_date == pc_date

        return raw_date

class Dataset(Model):
    """
    Model allows either RAW or PrincipalComponents foreign key to be passed as one field
    Unique=True for both fields DOES NOT apply to Nulls. This ensures no duplication
    of data objects
    """
    objects = DatasetManager()

    raw = OneToOneField("RAW", null=True, blank=True, unique=True, on_delete=CASCADE)
    pc = OneToOneField("PrincipalComponents", null=True, blank=True, unique=True, on_delete=CASCADE)

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        > Ensures raw or pc fields have correct values
        """
        if type(self.raw) != RAW and self.raw != None:
            raise IntegrityError("raw must be a RAW object or None")
        if type(self.pc) != PrincipalComponents and self.pc != None:
            raise IntegrityError("pc must be a PrincipalComponents object or None")

        if not self.raw and not self.pc:
            raise IntegrityError("""Both raw and pc fields cannot be null.""")
        if self.raw and self.pc:
            raise IntegrityError("""One of raw or pc fields must be null""")

        super().save(*args, **kwargs)

    def __str__(self):
        if self.raw:
            return "{} ".format(self.raw)
        elif self.pc:
            return "{} ".format(self.pc)

    def raw_or_pc(self):
        if self.raw:
            return self.raw
        elif self.pc:
            return self.pc

    def n_diffs(self):
        if self.raw:
            return self.raw.n_diffs
        elif self.pc:
            return self.pc.raw.n_diffs

    def inf(self):
        if self.raw:
            return self.raw.inflation
        elif self.pc:
            return self.pc.raw.inflation

    def output_gap(self):
        if self.raw:
            return self.raw.output_gap
        elif self.pc:
            return self.pc.raw.output_gap

    def df(self):
        """
        > Returns pandas DataFrame of data from the appropriate Dataset subset
        > external variables are not included in PC analysis
        > therefore, external variables must be attached to the Principal Components pulled from self.pc
        """
        if self.raw:
            df = pd.read_json(self.raw.json, orient="index")
        elif self.pc:
            df = pd.concat([pd.read_json(self.pc.json, orient="index"), self.pc.raw.external_df()], axis=1)
        
        df.index.names = ["date"]

        return df

    def nodiff_df(self):
        """
        Return DataFrame of undifferenced data if n_diffs != 0.
        If n_diffs == 0, return None
        """
        if self.n_diffs() == 0:
            return None
        else:
            if self.raw:
                df = pd.read_json(self.raw.orig_json, orient="index")
            elif self.pc:
                df = pd.read_json(self.pc.raw.orig_json, orient="index")

            df.index.names = ["date"]

            return df

    def end_date(self):
        if self.raw:
            return self.raw.last_date
        elif self.pc:
            return self.pc.raw.last_date

class RAW(Model):
    orig_json = JSONField("Original Historical Data")
    json = JSONField("Original or Differenced Data")
    last_date = DateField("Last Date in Dataset")

    inflation = BooleanField("Inflation")
    output_gap = BooleanField("Output Gap")
    n_diffs = IntegerField("Number of Differences", default=0,
                    validators=[MinValueValidator(0), MaxValueValidator(60)]
    )

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def __str__(self):
        return "{} INF {} GAP {} Diffs {}".format(
                    self.last_date, bool_string(self.inflation), bool_string(self.output_gap), self.n_diffs
        )

    @transaction.atomic
    def save(self, df, *args, **kwargs):
        """
        Custom Save does the following:
        1) Drops CPI and Output gap data from DF if fields are set to False
        2) Takes first/second/etc. order difference of data as per n_diffs
        3) sets last_date based on DF
        4) converts DF to json for storage in JSONField
        """
        df = df.copy()  # this allows multiple iterations of save() without alteration of df

        if not self.pk:
            self.date_added = timezone.now()
        self.date_modified = timezone.now()

        if not self.inflation:
            df = df.drop(columns="inflation", axis=1)
        if not self.output_gap:
            df = df.drop(columns="output_gap", axis=1)

        self.last_date = df.tail(1).index[0].to_pydatetime()

        # Have to convert datetime to string; otherwise JSON mangles conversion
        df.index = df.index.format()
        self.orig_json = df.to_json(orient="index")

        for i in range(self.n_diffs):
            df = df.diff().dropna()

        self.json = df.to_json(orient="index")

        super().save(*args, **kwargs)

    def yields_df(self):
        """
        Returns a Dataframe containing only yield data
        Columns are dropped from the json field according to inflation and output bools
        """

        df = pd.read_json(self.json, orient="index")
        if self.inflation:
            df = df.drop(["inflation"], axis=1)
        if self.output_gap:
            df = df.drop(["output_gap"], axis=1)

        df.index.names = ["date"]

        return df

    def external_df(self):
        """
        Returns a Dataframe containing only external variables
        Columns are selected according to external variable booleans
        """
        cols = []
        if self.inflation:
            cols.append("inflation")
        if self.output_gap:
            cols.append("output_gap")

        if self.inflation or self.output_gap:
            df = pd.read_json(self.json, orient="index")[cols]
        elif self.inflation is False and self.output_gap is False:
            df = pd.DataFrame()

        df.index.names = ["date"]

        return df

class PrincipalComponents(Model):
    raw = ForeignKey("RAW", on_delete=CASCADE)

    json = JSONField("Principal Component Data", null=True, blank=True)
    n = IntegerField("Number of Principal Components", null=True, blank=True)
    explained = ArrayField(FloatField(), null=True, blank=True)

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    class Meta:
        unique_together = ("raw", "n")

    def __str__(self):
        return "PC{} {}".format(self.n, self.raw)

    @transaction.atomic
    def save(self, df, *args, **kwargs):
        if not self.pk:
            self.date_added = timezone.now()
        self.date_modified = timezone.now()

        # Have to convert datetime to string; otherwise JSON mangles conversion
        df.index = df.index.format()
        self.json = df.to_json(orient="index")

        super().save(*args, **kwargs)

class Cointegration(Model):

    class DET(ChoiceEnum):
        """
        Deterministic provides regression structure to 3 different processes
            1) CointegrationAnalysis / augdicfull: values match statsmodels adfuller test
            2) CointegrationAnalysis / get_johansen:
                    values converted to fit statsmodels coint_johansen
            3) YieldCurveForecast: values are converted to fit statsmodels VECM
        "c" : constant only (default)
        "ct" : constant and trend
        "nc" : no constant, no trend
        """
        NC = "nc"
        C = "c"
        CT = "ct"

    class CRIT(ChoiceEnum):
        ONE = "1%"
        FIVE = "5%"
        TEN = "10%"

    class SIGNIF(ChoiceEnum):
        NINETY = "90%"
        NINETY_FIVE = "95%"
        NINETY_NINE = "99%"
        NULL = "Null Significance"

    dataset = ForeignKey("Dataset", on_delete=CASCADE)
    p = IntegerField("p-value for Cointegration Test", default=0,
                    validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    deterministic = CharField("Deterministic", choices=DET.choices(),
                                default="", max_length=3
    )
    root_crit = CharField("Critical Value for Root Test", choices=CRIT.choices(),
                            default="", max_length=10
    )
    any_roots = BooleanField("Any Roots")
    diffs_to_stationary = IntegerField("Differences to make Stationary")
    rank = IntegerField("Cointegration Rank", null=True)
    signif = CharField("Cointegration Signficance", choices=SIGNIF.choices(),
                                max_length=50, null=True
    )

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    class Meta:
        unique_together = ("dataset", "p", "deterministic", "root_crit")

    def __str__(self):
        return "Cointegration Analysis for Dataset: {}, p:{}, det:{}, root_crit:{}" \
                .format(self.dataset, self.p, self.deterministic, self.root_crit)

class TechniqueManager(Manager):
    def ps(self):
        var_ps = list(VAR.objects.values_list("p", flat=True))
        varma_ps = list(set(VARMA.objects.values_list("p", flat=True)))
        varma_ps.sort()
        vecm_ps = list(set(VECM.objects.values_list("p", flat=True)))
        vecm_ps.sort()
        ps = list(set(var_ps + varma_ps + vecm_ps))
        ps.sort()
        return ps

    def qs(self):
        qs = list(set(VARMA.objects.values_list("q", flat=True)))
        qs.sort()
        return qs

    def seasons(self):
        seasons = list(set(VECM.objects.values_list("seasons", flat=True)))
        seasons.sort()
        return seasons

class Technique(Model):
    objects = TechniqueManager()

    var = OneToOneField("VAR", null=True, blank=True, unique=True, on_delete=CASCADE)
    varma = OneToOneField("VARMA", null=True, blank=True, unique=True, on_delete=CASCADE)
    vecm = OneToOneField("VECM", null=True, blank=True, unique=True, on_delete=CASCADE)

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.var and not self.varma and not self.vecm:
            raise IntegrityError("""All fields cannot be null. You must input
                either a VAR, VARMA, or VECM object.""")
        if (self.var and self.varma) or (self.var and self.vecm) or (self.varma and self.vecm):
            raise IntegrityError("""Two fields must be null. Either only VAR, or only VARMA,
                or only VECM object must be provided, but not more than one of each object.""")

        super(Technique, self).save(*args, **kwargs)

    def __str__(self):
        if self.var:
            return "{} ".format(self.var)
        elif self.varma:
            return "{} ".format(self.varma)
        elif self.vecm:
            return "{} ".format(self.vecm)

    def technique(self):
        if self.var:
            return self.var
        elif self.varma:
            return self.varma
        elif self.vecm:
            return self.vecm

    def use_technique(self):
        if self.var:
            return "var"
        elif self.varma:
            return "varma"
        elif self.vecm:
            return "vecm"

class VAR(Model):
    p = IntegerField("p-value for VAR", default=0, unique=True)

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    def __str__(self):
        return "VAR p: {}".format(self.p)

class VARMA(Model):
    p = IntegerField("p-value for VARMA", default=0,
                    validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    q = IntegerField("q-value for VARMA", default=0,
                    validators=[MinValueValidator(1), MaxValueValidator(3)]
    )

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    class Meta:
        unique_together = ("p", "q",)

    def __str__(self):
        return "VARMA p: {}, q: {}".format(self.p, self.q)

class VECM(Model):

    class DET(ChoiceEnum):
        """
        Deterministic provides regression structure to 3 different processes
            1) CointegrationAnalysis / augdicfull: values match statsmodels adfuller test
            2) CointegrationAnalysis / get_johansen:
                    values converted to fit statsmodels coint_johansen
            3) YieldCurveForecast: values are converted to fit statsmodels VECM
        "c" : constant only (default)
        "ct" : constant and trend
        "nc" : no constant, no trend
        """
        NC = "nc"
        C = "c"
        CT = "ct"

    p = IntegerField("p-value for VECM", default=0,
                    validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    seasons = IntegerField("Seasons", default=0,
                    validators=[MinValueValidator(1), MaxValueValidator(72)]
    )
    deterministic = CharField("Deterministic", choices=DET.choices(), max_length=3)

    date_added = DateTimeField("Date and Time Added", auto_now_add=True)
    date_modified = DateTimeField("Date and Time Modified", auto_now=True)

    class Meta:
        unique_together = ("p", "seasons", "deterministic")

    def __str__(self):
        return "VECM p {} seasons {} det {})".format(
                    self.p, self.seasons, self.deterministic
        )
