from datetime import datetime as dt, date as dt_date

from django_select2.forms import Select2MultipleWidget

from django.forms import ValidationError, Form, ModelForm, CharField, DateField, MultipleChoiceField, \
                            FileField, DateInput, HiddenInput, TextInput, ModelChoiceField, \
                            CheckboxSelectMultiple, BooleanField, IntegerField, NumberInput


from .models import Forecast, Cointegration, VAR, VARMA, VECM

from robocondo.global_helpers import ChoiceEnum

class StatusForm(ModelForm):
    current = BooleanField(required=False, initial=False)

    class Meta:
        model = Forecast
        fields = ["current"]

    def __init__(self, i, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["current"].widget.attrs["class"] = "current_class" + str(i)

class ChartForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["number"].widget.attrs["style"] = "height:75px"

    P_CHOICES = tuple((p["p"], p["p"]) for p in VAR.objects.all().values("p"))
    Q_CHOICES = tuple((i, i) for i in  set(i[0] for i in VARMA.objects.all().values_list("q")))
    SEASONS_CHOICES = tuple((i, i) for i in  set(i[0] for i in VECM.objects.all().values_list("seasons")))

    # ps = [1, 12, 24, 36, 48, 60]
    # qs = [1, 2, 3]
    # seasons = [12, 24, 36, 48]
    #
    # P_CHOICES = tuple((p, p) for p in ps)
    # Q_CHOICES = tuple((q, q) for q in qs)
    # SEASONS_CHOICES = tuple((season, season) for season in seasons)

    top_forecasts = BooleanField(required=False, initial=False)
    number = IntegerField(required=False, localize=False, max_value=50, min_value=1)

    raw = BooleanField(required=False, initial=True)
    pc = BooleanField(required=False, initial=False)
    inflation = BooleanField(required=False, initial=False)
    output_gap = BooleanField(label="Output Gap", required=False, initial=False)
    var = BooleanField(required=False, initial=True)
    varma = BooleanField(required=False, initial=False)
    vecm = BooleanField(required=False, initial=False)
    p = MultipleChoiceField(required=False, widget=Select2MultipleWidget, choices=P_CHOICES)
    q = MultipleChoiceField(required=False, widget=Select2MultipleWidget, choices=Q_CHOICES)
    seasons = MultipleChoiceField(required=False, widget=Select2MultipleWidget, choices=SEASONS_CHOICES)
    deterministics = MultipleChoiceField(required=False, widget=Select2MultipleWidget, choices=[i[::-1] for i in Cointegration.DET.choices()])
