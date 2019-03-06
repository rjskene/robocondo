from datetime import datetime as dt, date, timedelta
from dateutil.relativedelta import relativedelta

from django.shortcuts import render
from django.utils import timezone

from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect
from django.forms.models import model_to_dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin

from django.views.generic.edit import CreateView, UpdateView, FormView
from django.views.generic.list import ListView
from django.views.generic.base import TemplateView

from rest_framework.viewsets import ModelViewSet

from guardian.mixins import PermissionRequiredMixin
from guardian.decorators import permission_required_or_403
from guardian.shortcuts import assign_perm

from .serializers import CondoSerializer
from .models import Condo, BankAccounts, AccountBalance, Investments
from .forms import BankAccountsForm, AccountBalanceForm, InvestmentsForm, CondoAssignForm

from reservefundstudy.models import Study, Contributions
from reservefundstudy.forms import RFSForm
from investmentplan.models import Plan
from gic_select.select import all_insureds

@login_required
@permission_required_or_403("condo.view_condo", (Condo, "id", "condo_id"))
def condo_main(request, **kwargs):
    """
    Main Condo View
    Displays Bank Account, Investment, and Reserve Fund Study info
    Allows create and update for Bank Accounts, Investments, and Reserve Fund Studies
    Creates forms for each instance.
    If request.POST, checks for correct form_name in request.POST and sets all other forms to None
    """
    # Setup Kwargs
    context = {}
    context["condo"] = Condo.objects.get(id=kwargs["condo_id"])
    context["condo_id"] = context["condo"].id
    context["study"] = Study.objects.get_or_none(condo=context["condo"], current=True, archived=False)
    context["plan"] = Plan.objects.get_or_none(study=context["study"], status_bool=True)

    # Account & Balance Info: creates one dictionary for all account and balance info & forms
    context["accounts"] = {}
    accounts = BankAccounts.objects.filter_archived(condo__id=context["condo"].id)
    if accounts:
        accounts = accounts.order_by("-type")
        # Store model instances to pre-populate form
        for account in accounts:
            context["accounts"][account.id] = {}
            context["accounts"][account.id]["account"] = account
            balance = AccountBalance.objects.filter_or_none(account__id=account.id)
            context["accounts"][account.id]["balance"] = balance.latest("date_added") if balance else balance

        # Adjust model instance values for presentation purposes
        accounts_insured = []
        for id, account in context["accounts"].items():
            context["accounts"][id]["table"] = model_to_dict(account["account"])
            context["accounts"][id]["table"]["spread"] = "{0:.2%}".format(account["account"].spread)
            context["accounts"][id]["table"]["balance"] = "$ {:,.2f}".format(account["balance"].balance) if account["balance"] else "Input Account Balance"
            context["accounts"][id]["table"]["balance_date"] = account["balance"].date.strftime("%d %b %Y") if account["balance"] else "---"
            context["accounts"][id]["table"]["insured"] = account["account"].institution in all_insureds()
            accounts_insured.append(context["accounts"][id]["table"]["insured"])

        context["all_accounts_insured"] = all(accounts_insured)

    context["num_accounts"] = len(context["accounts"])

    # Investments
    context["investments"] = {}
    invmts = Investments.objects.current(condo=context["condo"])
    context["maturing"] = []
    if invmts:
        invmts = invmts.order_by("-maturity_date")
        # Stores the model instance for each investment to be edited
        for invmt in invmts:
            context["investments"][invmt.id] = {}
            context["investments"][invmt.id]["invmt"] = invmt

        # Modifies instance values for table presentation purposes
        invmts_insured = []
        for id, invmt in context["investments"].items():
            context["investments"][id]["table"] = model_to_dict(invmt["invmt"])
            context["investments"][id]["table"]["interest_rate"] = "{0:.2%}".format(invmt["invmt"].interest_rate)
            context["investments"][id]["table"]["amount"] = "${:,.2f}".format(invmt["invmt"].amount)
            context["investments"][id]["table"]["maturity_date"] = invmt["invmt"].maturity_date.strftime("%d %b %Y")
            context["investments"][id]["table"]["insured"] = invmt["invmt"].institution in all_insureds()
            if invmt["invmt"].maturity_date < timezone.make_aware(dt.now()) + relativedelta(months=1):
                context["maturing"].append(invmt["invmt"])

            invmts_insured.append(context["investments"][id]["table"]["insured"])

        context["all_invmts_insured"] = all(invmts_insured)

    context["num_invmts"] = len(context["investments"])
    context["notifications"] = len(context["maturing"]) if context["maturing"] else None

    # Reserve Fund Studies
    context["studies"] = {}
    studies = Study.objects.filter_or_none(condo=context["condo"], archived=False)
    if studies:
        studies = studies.order_by("-current", "-date")
        for study in studies:
            context["studies"][study.id] = {}
            context["studies"][study.id]["study"] = study
            context["studies"][study.id]["date"] = study.date.strftime("%d %b %Y")
            context["studies"][study.id]["flows"] = Contributions.objects.filter(study=study).exists()

    context["num_studies"] = len(context["studies"])

    # Top Cards
    balance = (
                sum(context["accounts"][account_id]["balance"].balance if context["accounts"][account_id]["balance"] else 0 \
                    for account_id, values in context["accounts"].items() \
                    if context["accounts"][account_id]["balance"] is not None \
                    and context["accounts"][account_id]["account"].type == BankAccounts.Type.RESERVE.name
                ) \
                + sum(values["invmt"].amount for invmt_id, values in context["investments"].items())
    )
    context["balance"] = "${:,.2f}".format(balance)

    if request.method == 'POST':
        # Accounts: create forms
        context["create_account_form"] = BankAccountsForm(request.POST) if "create_account_form" in request.POST else None
        account_forms = {}
        for account_id, values in context["accounts"].items():
            update_account_name = "update_account_form" + str(account_id)
            context["accounts"][account_id]["table"]["update_account_form"] = \
                BankAccountsForm(request.POST, instance=values["account"]) if update_account_name in request.POST else None
            create_balance_name = "create_balance_form" + str(account_id)
            context["accounts"][account_id]["table"]["create_balance_form"] = AccountBalanceForm(request.POST) if create_balance_name in request.POST else None
            account_forms[account_id] = {}
            account_forms[account_id]["update_account_form"] = context["accounts"][account_id]["table"]["update_account_form"]
            account_forms[account_id]["create_balance_form"] = context["accounts"][account_id]["table"]["create_balance_form"]

        # Investments: create forms
        context["create_invmt_form"] = InvestmentsForm(request.POST) if "create_invmt_form" in request.POST else None
        invmt_forms = {}
        for invmt_id, values in context["investments"].items():
            update_invmt_name = "update_invmt_form" + str(invmt_id)
            context["investments"][invmt_id]["table"]["update_invmt_form"] = \
                InvestmentsForm(request.POST, instance=values["invmt"]) if update_invmt_name in request.POST else None
            invmt_forms[invmt_id] = {}
            invmt_forms[invmt_id]["update_invmt_form"] = context["investments"][invmt_id]["table"]["update_invmt_form"]

        # Studies: create forms
        context["create_study_form"] = RFSForm(request.POST, request.FILES) if "create_study_form" in request.POST else None
        study_forms = {}
        for study_id, values in context["studies"].items():
            update_study_name = "update_study_form" + str(study_id)
            context["studies"][study_id]["update_study_form"] = \
                RFSForm(request.POST, request.FILES, instance=values["study"]) if update_study_name in request.POST else None
            study_forms[study_id] = {}
            study_forms[study_id]["update_study_form"] = context["studies"][study_id]["update_study_form"]

        # Accounts Create: Validate & Save
        if context["create_account_form"] is not None and context["create_account_form"].is_valid():
            context["create_account_form"].save(condo=context["condo"])
            messages.success(request, "The Form was completed successfully.", extra_tags="submit_success")
            return redirect(reverse("condo:main", kwargs=kwargs))

        # Accounts Update: Validate and save
        for account_id, values in account_forms.items():
            if values["update_account_form"] is not None and values["update_account_form"].is_valid():
                values["update_account_form"].save(condo=context["condo"])
                messages.success(request, "The Form was completed successfully.", extra_tags="submit_success")
                return redirect(reverse("condo:main", kwargs=kwargs))
            if values["create_balance_form"] is not None and values["create_balance_form"].is_valid():
                values["create_balance_form"].save(account=context["accounts"][account_id]["account"])
                messages.success(request, "The Account Balance was updated successfully.", extra_tags="submit_success")
                return redirect(reverse("condo:main", kwargs=kwargs))

        # Investments Create: Validate & Save
        if context["create_invmt_form"] is not None and context["create_invmt_form"].is_valid():
            context["create_invmt_form"].save(condo=context["condo"])
            messages.success(request, "The Form was completed successfully.", extra_tags="submit_success")
            return redirect(reverse("condo:main", kwargs=kwargs))

        # Investments Update: Validate and save
        for invmt_id, values in invmt_forms.items():
            if values["update_invmt_form"] is not None and values["update_invmt_form"].is_valid():
                values["update_invmt_form"].save(condo=context["condo"])
                messages.success(request, "The Form was completed successfully.", extra_tags="submit_success")
                return redirect(reverse("condo:main", kwargs=kwargs))

        # Studies Create: Validate & Save
        if context["create_study_form"] is not None and context["create_study_form"].is_valid():
            context["create_study_form"].save(condo=context["condo"])
            messages.success(request, "The Form was completed successfully.", extra_tags="submit_success")
            return redirect(reverse("condo:main", kwargs=kwargs))

        # Studies Update: Validate and save
        for study_id, values in study_forms.items():
            if values["update_study_form"] is not None and values["update_study_form"].is_valid():
                values["update_study_form"].save(condo=context["condo"])
                messages.success(request, "The Form was completed successfully.", extra_tags="submit_success")
                return redirect(reverse("condo:main", kwargs=kwargs))
        else:
            # Must re-instantiate all forms that were not submitted and set to None
            if context["create_account_form"] is None:
                context["create_account_form"] = BankAccountsForm()
            for account_id, values in account_forms.items():
                if values["update_account_form"] is None:
                    context["accounts"][account_id]["table"]["update_account_form"] = BankAccountsForm(instance=context["accounts"][account_id]["account"])
                if values["create_balance_form"] is None:
                    context["accounts"][account_id]["table"]["create_balance_form"] = AccountBalanceForm()
            if context["create_invmt_form"] is None:
                context["create_invmt_form"] = InvestmentsForm()
            for invmt_id, values in invmt_forms.items():
                if values["update_invmt_form"] is None:
                    context["investments"][invmt_id]["table"]["update_invmt_form"] = InvestmentsForm(instance=context["investments"][invmt_id]["invmt"])
            if context["create_study_form"] is None:
                context["create_study_form"] = RFSForm()
            for study_id, values in study_forms.items():
                if values["update_study_form"] is None:
                     context["studies"][study_id]["update_study_form"] = RFSForm(instance=context["studies"][study_id]["study"])

            messages.error(request, "The Form was completed incorrectly.", extra_tags="error_warning")
            return render(request, "condo/condo_main.html", context)
    else:
        context["create_account_form"] = BankAccountsForm()
        for account_id, account in context["accounts"].items():
            account["table"]["update_account_form"] = BankAccountsForm(instance=account["account"])
            account["table"]["create_balance_form"] = AccountBalanceForm()

        context["create_invmt_form"] = InvestmentsForm()
        for invmt_id, invmt in context["investments"].items():
            invmt["table"]["update_invmt_form"] = InvestmentsForm(instance=invmt["invmt"])

        context["create_study_form"] = RFSForm()
        for study_id, values in context["studies"].items():
            values["update_study_form"] = RFSForm(instance=values["study"], initial={"current": values["study"].current})

        return render(request, "condo/condo_main.html", context)

@login_required
@permission_required_or_403("condo.view_condo", (Condo, "id", "condo_id"))
def invmt_archive_view(request, **kwargs):
    """
    Archive an investment that User no longer wishes to view or has matured
    """
    invmt = Investments.objects.get(id=kwargs["invmt_id"])
    invmt.archived = True
    invmt.save()

    kwargs.pop("invmt_id", None)
    return redirect(reverse("condo:main", kwargs=kwargs))

@login_required
@permission_required_or_403("condo.view_condo", (Condo, "id", "condo_id"))
def account_archive_view(request, **kwargs):
    """
    Archive an investment that User no longer wishes to view or has matured
    """
    account = BankAccounts.objects.get(id=kwargs["account_id"])
    account.archived = True
    account.save()

    kwargs.pop("account_id", None)
    return redirect(reverse("condo:main", kwargs=kwargs))

class CondoAssign(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """
    Page for assigning Users to Condos
    """
    template_name = "condo/condo_assign_form.html"
    form_class = CondoAssignForm

    def form_valid(self, form):
        """
        Custom form_valid extension to make permission changes based on selections
        """
        for condo in form.cleaned_data["condos"]:
            for user in form.cleaned_data["users"]:
                if not user.has_perm("view_condo"):
                    assign_perm("view_condo", user, condo)

                for study in Study.objects.filter(condo=condo):
                    if not user.has_perm("view_study"):
                        assign_perm("view_study", user, study)

        return super().form_valid(form)

    def get_success_url(self):
        self.success_url = reverse_lazy("accountmanager:dashboard", args=(self.request.user.username,))
        return super().get_success_url()

    def test_func(self):
        return self.request.user.is_staff

class CondoCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Add a new Condo
    """
    model = Condo
    fields = ["name"]
    template_name_suffix = "_create_form"

    def get_success_url(self):
        self.success_url = reverse_lazy("accountmanager:dashboard", args=(self.request.user.username,))

        return super().get_success_url()

    def test_func(self):
        return self.request.user.is_staff

class CondoViewSet(ModelViewSet):
    """
    API endpoint that allows Condos to be viewed or edited.
    """
    queryset = Condo.objects.all().order_by("-date_added")
    serializer_class = CondoSerializer
