import pandas as pd

from django.forms import CharField, EmailField, DateField, ModelForm, DateInput, \
                        FileField, Form, HiddenInput

from reservefundstudy.models import Study
from reservefundstudy.forms import RFSForm

class RFSDemoForm(RFSForm):

    class Meta(RFSForm.Meta):
        RFSForm.Meta.exclude += ["current"]

    def save(self, commit=False, *args, **kwargs):
        instance = super().save(condo=None, commit=False, *args, **kwargs)
        instance.years = self.years
        # instance.years = instance.last_year - instance.first_year + 1
        print (self.cleaned_data["file"])

        # df = pd.read_csv(self.cleaned_data["file"], encoding="ISO-8859-1")
        # conts = {"cont_year_{}".format(k + 1): v for k, v in df["Contributions"].iteritems()}
        # exps = {"exp_year_{}".format(k + 1): v for k, v in df["Expenditures"].iteritems()}

        conv_kwargs = {
                "opening_balance": instance.opening_balance, "contributions": self.conts,
                "expenditures": self.exps, "first_year": instance.first_year,
                "last_year": instance.last_year, "years": instance.years
        }

        return conv_kwargs
