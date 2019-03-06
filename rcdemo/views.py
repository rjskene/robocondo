from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
import requests

from celery.result import AsyncResult

from django.http import HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic.base import TemplateView

from investmentplan.charts import bank_chart, alloc_chart, contsexps_chart, total_chart
from gic_select.models import GICs, GICPlan, GICSelect
from gic_select.select import gic_select

class DemoPlanView(TemplateView):
    """
    Main landing page for each Plan
    """
    template_name = "rcdemo/plan_main.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        r = requests.get(self.request.build_absolute_uri(reverse("rcdemo:get-progress", kwargs=kwargs)))

        if r.json()["state"] == "SUCCESS":
            context["forecast"] = r.json()["details"]["forecast"]
            context["details"] = r.json()["details"]["study_details"]

            for i, record in enumerate(context["forecast"]):
                record["month"] = dt(context["details"]["first_year"], 1, 1) + relativedelta(months=i)

            # invmts = {term: value for term, value in context["forecast"][0].items() if term[0:4] == "term"}
            # last_date = GICs.objects.latest("date").date
            # gics = GICs.objects.filter(date=last_date)
            # selected = gic_select(invmts, gics)
            # print (selected)
            # context["gic_recommends"] = GICSelect.objects.filter(gic_plan=context["gic_plan"])

            years = [dt(context["details"]["first_year"] + i, 1, 1) for i in range(context["details"]["years"])]
            annual_conts = []
            for year in years:
                annual_conts.append({"year": year})
            for i, cont in enumerate(context["details"]["contributions"].values()):
                if i < context["details"]["years"]:
                    annual_conts[i]["total"] = cont

            annual_exps = []
            for year in years:
                annual_exps.append({"year": year})
            for i, exp in enumerate(context["details"]["expenditures"].values()):
                if i < context["details"]["years"]:
                    annual_exps[i]["total"] = exp

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
                        record[name] = "{:.2f}".format(value)
                record["month"] = record["month"].date().strftime("%b %Y")

        return context

def demo_progress_view(request, task_id):
    if request.POST:
        return redirect(reverse("rcdemo:plan", kwargs={"task_id": task_id}))
    return render(request, "rcdemo/progress_bar.html", context={"task_id": task_id})

def demo_get_progress(request, task_id):
    result = AsyncResult(task_id)
    response_data = {
        "state": result.state,
        "details": result.info,
    }
    return JsonResponse(response_data)
