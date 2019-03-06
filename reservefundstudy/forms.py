import pandas as pd
from django.forms import CharField, EmailField, DateField, ModelForm, DateInput, \
                        FileField, Form, HiddenInput, BooleanField, CheckboxInput, \
                        ValidationError
from django.db import transaction

from .models import Study, Contributions, Expenditures

class RFSForm(ModelForm):
    date = DateField(
                        widget=DateInput(format = "%d-%m-%Y"),
                        input_formats=["%d-%m-%Y",]
    )
    file = FileField(required=False, label="Upload Contributions & Expenditures")

    class Meta:
        model = Study
        exclude = ["condo", "years", "archived"]

    def clean(self):
        cleaned_data = super().clean()
        self.years = cleaned_data["last_year"] - cleaned_data["first_year"] + 1

        if cleaned_data["file"]:
            df = pd.read_csv(cleaned_data["file"], encoding = "ISO-8859-1")
            self.conts = {"cont_year_{}".format(k + 1): v for k, v in df["Contributions"].iteritems()}
            self.exps = {"exp_year_{}".format(k + 1): v for k, v in df["Expenditures"].iteritems()}

            if len(self.conts) < self.years:
                raise ValidationError("There was an error with the inputs. The First Year and Last Year fields suggest a study period of {} years, while the contributions and expenditures file suggest {} years".format(self.years, len(self.conts)))

            if len(self.conts) != len(self.exps):
                raise ValidationError("There was an error with the uploaded file. Contributions and Expenditures must have an equal number of years.")

    def save(self, condo, commit=True, *args, **kwargs):
        instance = super().save(commit=False, *args, **kwargs)
        instance.years = self.years
        instance.condo = condo
        instance.current = True if "current" in self.data else False

        if commit:
            instance.save()

            if self.cleaned_data["file"]:
                with transaction.atomic():
                    Contributions.objects.create(study=instance, **self.conts)
                    Expenditures.objects.create(study=instance, **self.exps)

        return instance

class ContForm(ModelForm):
    class Meta:
        model = Contributions
        exclude = ["study"]

    def __init__(self, *args, **kwargs):
        """
        The form dynamically selects the input fields based on the years selected
        for the study.
        An extra kwarg is passed from the view to determine years not required.
        """
        excluded_years = kwargs.pop("excluded_years")
        super(ContForm, self).__init__(*args, **kwargs)
        for year in excluded_years:
            if ("cont_" + year) in self.fields:
                del self.fields["cont_" + year]

class ExpForm(ModelForm):
    class Meta:
        model = Expenditures
        exclude = ["study"]

    def __init__(self, *args, **kwargs):
        """
        The form dynamically selects the input fields based on the years selected
        for the study.
        An extra kwarg is passed from the view to determine years not required.
        """
        excluded_years = kwargs.pop("excluded_years")
        super(ExpForm, self).__init__(*args, **kwargs)
        for year in excluded_years:
            if ("exp_" + year) in self.fields:
                del self.fields["exp_" + year]
