from datetime import datetime as dt

from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, FactorRange, Range1d, SingleIntervalTicker, LinearAxis
from bokeh.models.sources import AjaxDataSource
from bokeh.palettes import Blues, Category20b, Category20c
from bokeh.transform import factor_cmap, dodge
from bokeh.core.properties import value as val

from bokeh.embed import components
from bokeh.embed import server_session
from bokeh.util import session_id

from celery.exceptions import TimeLimitExceeded

from django.db.models.functions import TruncMonth, TruncYear
from django.db.models import Avg, Count, Min, Sum

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from django.views.generic.base import TemplateView

from celery.result import AsyncResult

from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated

from guardian.mixins import PermissionRequiredMixin
from guardian.decorators import permission_required_or_403

from .serializers import PlanSerializer, ForecastSerializer
from .models import Plan, Forecast
from .tasks import pyondo_task
from .helpers import find_dates, current_investments
from .charts import bank_chart, alloc_chart, contsexps_chart, total_chart

from condo.models import Condo, BankAccounts, AccountBalance, Investments
from reservefundstudy.models import Study

from gic_select.models import GICPlan, GICSelect

class PlanView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Main landing page for each Plan
    """
    model = Plan
    template_name = "investmentplan/plan_main.html"
    permission_required = "condo.view_condo"
    return_403 = True

    def dispatch(self, request, *args, **kwargs):
        self.condo = Condo.objects.get(pk=self.kwargs["condo_id"])
        return super(PlanView, self).dispatch(request, *args, **kwargs)

    def get_object(self):
        return self.condo

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["condo_id"] = self.condo.id
        context["condo"] = self.condo
        context["study"] = Study.objects.get(condo=self.condo, current=True)
        context["plan"] = Plan.objects.get(status_bool=True, study=context["study"])
        forecast = Forecast.objects.filter(plan=context["plan"]).order_by("period")
        context["forecast"] = list(forecast.values())
        context["gic_plan"] = GICPlan.objects.get(status_bool=True)
        recommends = GICSelect.objects.filter(gic_plan=context["gic_plan"])
        context["gic_recommends"] = list(recommends.values(
                                        "gic__issuer",
                                        "gic__term",
                                        "gic__rate",
                                        "amount"
                                    )
        )

        total_recommended_invmt = sum(i["amount"] for i in context["gic_recommends"])
        context["total_recommended_invmt"] = "$ {:,.2f}".format(total_recommended_invmt)

        invmts = Investments.objects.current(condo=context["condo"])
        total_current_invmt = sum(invmt.amount for invmt in invmts)
        context["total_current_invmt"] = "$ {:,.2f}".format(total_current_invmt)

        accounts = BankAccounts.objects.filter_or_none(condo__id=context["condo"].id)
        balances = {}
        for account in accounts:
            if account.type == BankAccounts.Type.RESERVE.name:
                balances[account.id] = AccountBalance.objects.filter_or_none(account__id=account.id).latest("date_added")

        balance = (
                sum(balance.balance for id, balance in balances.items() if balance is not None) + total_current_invmt
        )
        context["balance"] = "{:,.2f}".format(balance)

        for record in context["gic_recommends"]:
            for name, value in record.items():
                if name == "gic__rate":
                    record[name] = '{:.2%}'.format(value)
                elif isinstance(value, float):
                    record[name] = "$ {:,.2f}".format(value)

        annual_conts = list(forecast.annotate(year=TruncYear("month")). \
                                values("year"). \
                                annotate(total=Sum("contributions")). \
                                order_by()
        )
        annual_exps = list(forecast.annotate(year=TruncYear("month")). \
                                values("year"). \
                                annotate(total=Sum("expenditures")). \
                                order_by()
        )
        from operator import itemgetter
        annual_conts = sorted(annual_conts, key=itemgetter("year"))
        annual_conts = [dct["total"] for dct in annual_conts]
        annual_exps = sorted(annual_exps, key=itemgetter("year"))
        annual_exps = [dct["total"] for dct in annual_exps]

        context["bank"] = bank_chart(context["forecast"])
        context["allocation"] = alloc_chart(context["forecast"])
        context["contsexps"] = contsexps_chart(context["forecast"], annual_conts, annual_exps)
        context["total"] = total_chart(context["forecast"], annual_exps)

        for record in context["forecast"]:
            for name, value in record.items():
                if isinstance(value, float):
                    record[name] = "$ {:,.2f}".format(value)
            record["month"] = record["month"].date().strftime("%b %Y")

        return context

@login_required
@permission_required_or_403("condo.view_condo", (Condo, "id", "condo_id"))
def run_robocondo(request, **kwargs):
    result = pyondo_task.delay(kwargs["condo_id"], kwargs["rfs_id"])
    kwargs["task_id"] = result.task_id
    return redirect(reverse("investmentplan:progress", kwargs=kwargs))

@login_required
@permission_required_or_403("condo.view_condo", (Condo, "id", "condo_id"))
def progress_view(request, **kwargs):
    if request.POST:
        plan = Plan.objects.get(study__id=kwargs["rfs_id"], status_bool=True)
        kwargs["plan_id"] = plan.id
        kwargs.pop("task_id", None)
        return redirect(reverse("investmentplan:plan-main", kwargs=kwargs))
    return render(request, "investmentplan/progress_bar.html", context=kwargs)

@login_required
@permission_required_or_403("condo.view_condo", (Condo, "id", "condo_id"))
def get_progress(request, **kwargs):
    result = AsyncResult(kwargs["task_id"])

    insufficient = False
    if isinstance(result.info, TypeError) and str(result.info) == "unsupported operand type(s) for +: 'float' and 'NoneType'":
        insufficient = True
    time_limit_exceeded = True if isinstance(result.info, TimeLimitExceeded) else False
    
    response_data = {
        "state": result.state,
        "details": str(result.info) if insufficient or time_limit_exceeded else result.info
    }
    return JsonResponse(response_data)
