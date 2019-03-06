import datetime

from django.contrib.auth.models import User
from django.forms import Select, CharField, ChoiceField, EmailField, DateTimeField, \
                    DateField, ModelForm, Form, DateInput, HiddenInput, ModelMultipleChoiceField, \
                    TextInput, ValidationError

from django.contrib.admin.widgets import FilteredSelectMultiple

from .models import BankAccounts, AccountBalance, Investments, Condo
from gic_select import select

class CondoAssignForm(Form):
    users = ModelMultipleChoiceField(queryset=User.objects.all(), widget=FilteredSelectMultiple("verbose name", is_stacked=False))
    condos = ModelMultipleChoiceField(queryset=Condo.objects.all(), widget=FilteredSelectMultiple("verbose name", is_stacked=False))

class BankAccountsForm(ModelForm):

    class Meta:
        model = BankAccounts
        exclude = ["condo", "archived"]

    def __init__(self, *args, **kwargs):
        insureds = sorted(select.all_insureds(), key=str.lower)
        super().__init__(*args, **kwargs)

        self.fields["institution"].widget = ListTextWidget(data_list=insureds, name="insureds_list")

    def save(self, condo, commit=True, *args, **kwargs):
        instance = super().save(commit=False, *args, **kwargs)
        instance.condo = condo

        if commit:
            instance.save()

        return instance

class AccountBalanceForm(ModelForm):
    date = DateTimeField(
                        widget=DateInput(format="%d-%m-%Y"),
                        input_formats=["%d-%m-%Y",]
    )

    class Meta:
        model = AccountBalance
        exclude = ["account"]

    def save(self, account, commit=True, *args, **kwargs):
        instance = super().save(commit=False, *args, **kwargs)
        instance.account = account
        if commit:
            instance.save()

        return instance

def maturity_date_check(value):
    if value < datetime.date.today():
        raise ValidationError("Maturity date must be on or after today's date")
    return value

class InvestmentsForm(ModelForm):
    maturity_date = DateField(
                        widget=DateInput(format="%d-%m-%Y"),
                        input_formats=["%d-%m-%Y",], validators=[maturity_date_check]
    )

    class Meta:
        model = Investments
        exclude = ["condo", "archived"]

    def __init__(self, *args, **kwargs):
        insureds = sorted(select.all_insureds(), key=str.lower)
        super().__init__(*args, **kwargs)

        self.fields["institution"].widget = ListTextWidget(data_list=insureds, name="insureds_list")

    def save(self, condo, commit=True, *args, **kwargs):
        instance = super().save(commit=False, *args, **kwargs)
        instance.condo = condo

        if commit:
            instance.save()

        return instance

class ListTextWidget(TextInput):

    def __init__(self, data_list, name, *args, **kwargs):
        super(ListTextWidget, self).__init__(*args, **kwargs)
        self._name = name
        self._list = data_list
        self.attrs.update({'list':'list__%s' % self._name})

    def render(self, name, value, attrs=None, renderer=None):
        text_html = super(ListTextWidget, self).render(name, value, attrs=attrs)
        data_list = '<datalist id="list__%s">' % self._name
        for item in self._list:
            data_list += '<option value="%s">' % item
        data_list += '</datalist>'

        return (text_html + data_list)
