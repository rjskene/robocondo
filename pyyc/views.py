from datetime import datetime as dt
import pandas as pd

from django_tables2 import RequestConfig

from django.db.models import Count, Min, Sum, Avg, Q
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required

from django.views.generic.edit import CreateView, UpdateView

from django.views.generic.list import ListView
from django.views.generic.base import TemplateView
from django.urls import reverse, reverse_lazy

from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated

from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, NumeralTickFormatter, Legend

from bokeh.palettes import Blues, Category20b, Category20c
from bokeh.embed import components
from bokeh.embed import server_session
from bokeh.util import session_id

from celery.result import AsyncResult

from .serializers import ForecastSerializer, BOCGICForecastSerializer, DatasetSerializer, \
                            RAWSerializer, PrincipalComponentsSerializer, CointegrationSerializer, \
                            TechniqueSerializer, VARSerializer, VARMASerializer, VECMSerializer
from .models import HistoricalYieldCurve as HYC, HistoricalOvernightRate as HOR, \
                        InflationRate as INFR, OutputGap as GAP, BOCGICs, \
                        Forecast, BOCGICForecast, Dataset, RAW, PrincipalComponents as PC, \
                        Cointegration as COINT, Technique as TECH, VAR, VARMA, VECM
from .data.combine import make_frame
from .tasks import update_data_task, run_forecast_task
from .forms import ChartForm, StatusForm
from .tables import ForecastsTable
from .pyyc.main import PYYC
from gic_select.models import GICs


def line_plots(df, legend=False, width=450, height=300, excluded=[], months=None, **kwargs):
    x = df.index.name
    excluded.append(x)
    source = ColumnDataSource(df)

    plot = figure(
        x_axis_type="datetime",
        plot_width=width,
        plot_height=height,
        toolbar_location=None,
        **kwargs
    )

    legend_items = []
    for i, col in enumerate(df.columns):
        if col not in excluded:
            line = plot.line(x=x, y=col, line_width=2, source=source, color=Category20c[20][i])
            legend_items.append((col, [line]))
    plot.ygrid.grid_line_color = None
    plot.xgrid.grid_line_color = None
    plot.xaxis.axis_label = "Year"
    plot.xaxis.axis_label_standoff = 20
    plot.outline_line_color = None
    plot.yaxis[0].formatter = NumeralTickFormatter(format="0.0%")


    if legend:
        plot_legend = Legend(items=legend_items, location=(40, 0))

        plot.add_layout(plot_legend, "right")
        plot.legend.visible = legend

    script, div = components(plot)

    dct = {}
    dct["script"] = script
    dct["div"] = div

    return dct

@staff_member_required
def main_view(request):
    """
    Main landing page for each Yield Curve Forecast
    """
    context = {}

    # Make Current Yield Curve Chart
    df_hyc = make_frame(HYC)
    df_curr = df_hyc.copy()[-1:]
    cols =[
            "three_month", "six_month", "one_year", "two_year", "three_year",
            "four_year", "five_year", "seven_year", "ten_year", "twenty_five_year"
    ]
    df_curr = df_curr[cols].T
    df_curr = df_curr.rename({
        "three_month": "3", "six_month": "6", "one_year": "12", "two_year": "24",
        "three_year": "36", "four_year": "48", "five_year": "60", "seven_year": "84",
        "ten_year": "120", "twenty_five_year": "300"
    })
    plot = figure(x_range=df_curr.index.tolist(), width=575, height=300, toolbar_location=None)
    plot.line(x=df_curr.index.tolist(), y=df_curr[df_curr.columns[0]].tolist())
    plot.yaxis[0].formatter = NumeralTickFormatter(format="0.0%")
    plot.xaxis.axis_label = "Term (Months)"
    plot.xaxis.axis_label_standoff = 20
    plot.ygrid.grid_line_color = None
    plot.xgrid.grid_line_color = None
    plot.outline_line_color = None
    script, div = components(plot)

    context["dataset_last_date"] = Dataset.objects.latest_last_date()
    context["current"] = {}
    context["current"]["date"] = df_hyc.index[-1].to_pydatetime().date()
    context["current"]["div"] = div
    context["current"]["script"] = script

    # Make Historical Overnight Rate chart
    df_hor = make_frame(HOR)
    context["HOR"] = line_plots(df_hor["2009-01-31":], width=575, height=300)

    # Make Historical Yield Curve Chart
    context["HYC"] = line_plots(df_hyc["2009-01-31":], width=700, height=325, legend=True)

    # Make GIC Table
    gics = GICs.objects.latest_gics()
    gic_table = [{"date": gic.date.strftime("%d %b %Y"), "issuer": gic.issuer} for gic in gics.distinct("issuer")]
    for gic in gic_table:
        terms = GICs.objects.filter(issuer=gic["issuer"])
        for term in terms:
            gic[term.term] = "{:.2%}".format(term.rate)
    context["gic_table"] = gic_table
    context["gics_date"] = gics[0].date

    # Create table and charts for the current Forecast
    current = Forecast.objects.get_or_none(current=True)
    current_forecast_formatted = {}
    for date, record in current.df().to_dict("index").items():
        current_forecast_formatted[date.strftime("%b %Y")] = {}
        for term, value in record.items():
            if isinstance(value, float):
                current_forecast_formatted[date.strftime("%b %Y")][term] = "{:.2%}".format(value)

    excluded = ["inflation", "output_gap"]
    context["forecasts"] = {}
    context["forecasts"]["current_forecast"] = {}
    context["forecasts"]["current_forecast"]["object"] = current
    context["forecasts"]["current_forecast"]["name"] = current.__str__()
    context["forecasts"]["current_forecast"]["YC"] = {}
    context["forecasts"]["current_forecast"]["YC"]["table"] = current_forecast_formatted
    context["forecasts"]["current_forecast"]["YC"]["chart"] = line_plots(current.df(), width=550, legend=True, excluded=excluded)
    context["forecasts"]["current_forecast"]["GIC"] = {}
    context["forecasts"]["current_forecast"]["GIC"]["chart"] = line_plots(current.bocgicforecast.df(), width=550, legend=True, excluded=excluded)

    # Make Forecast selector forms and charts
    select = request.session.get("select")
    if select is None:
        forecasts = Forecast.objects.top_forecasts(10)
    elif select["top_forecasts"]:
        forecasts = Forecast.objects.top_forecasts(select["number"])
    else:
        forecasts = Forecast.objects.latest_group()
        forecasts = forecasts.filter(
            (Q(dataset__raw__isnull=not select["raw"]) | Q(dataset__pc__isnull=not select["pc"]))
        ).filter(Q(dataset__raw__inflation=select["inflation"])
                & Q(dataset__raw__output_gap=select["output_gap"])
                | (Q(dataset__pc__raw__inflation=select["inflation"])
                & Q(dataset__pc__raw__output_gap=select["output_gap"]))
        )
        vars = forecasts.filter(
                    technique__var__isnull=not select["var"],
                    technique__var__p__in=[int(i) for i in select["p"]]
        )
        varmas = forecasts.filter(
                    technique__varma__isnull=not select["varma"],
                    technique__varma__p__in=[int(i) for i in select["p"]],
                    technique__varma__q__in=[int(i) for i in select["q"]],
        )
        vecms = forecasts.filter(
                    technique__vecm__isnull=not select["vecm"],
                    technique__vecm__p__in=[int(i) for i in select["p"]],
                    technique__vecm__seasons__in=[int(i) for i in select["seasons"]],
                    technique__vecm__deterministic__in=select["deterministics"],
        )
        forecasts = vars.union(varmas, vecms).order_by("total_rmse")

    # Make dict of Forecasts chosen from Selector
    context["forecasts"]["objects"] = {}
    for i, forecast in enumerate(forecasts):
        df = forecast.df()
        context["forecasts"]["objects"][i] = {}
        context["forecasts"]["objects"][i]["obj"] = forecast
        context["forecasts"]["objects"][i]["YC"] = line_plots(df, excluded=excluded)
        df = forecast.bocgicforecast.df()
        context["forecasts"]["objects"][i]["GIC"] = line_plots(df, excluded=excluded)
    context["forecasts"]["count"] = forecasts.count()
    context["forecasts"]["date_added"] = forecasts[0].date_added if forecasts else None
    context["forecasts"]["end_date"] = Forecast.objects.last_date()

    if request.method == "POST":
        context["form"] = ChartForm(data=request.POST) if "forecast_filter" in request.POST else None

        status_forms = {}
        for i, forecast in enumerate(forecasts):
            set_current_name = "set_current" + str(i)
            status_forms[i] = {}
            status_forms[i] = StatusForm(data=request.POST, instance=forecast, i=i) if set_current_name in request.POST else None

        if context["form"] is not None and context["form"].is_valid():
            request.session["select"] = context["form"].cleaned_data

            return redirect(reverse("pyyc:main"))

        for id, form in status_forms.items():
            if form is not None and form.is_valid():
                form.save()
                return redirect(reverse("pyyc:main"))

        else:
            if context["form"] is None:
                context["form"] = ChartForm()
            for id, form in status_forms.items():
                if form is None:
                    context["forecasts"]["objects"][id]["form"] = StatusForm()

            return render(request, "pyyc/pyyc_main.html", context)
    else:
        context["form"] = ChartForm()

        for i, forecast in enumerate(forecasts):
            context["forecasts"]["objects"][i]["form"] = StatusForm(instance=forecast, i=i)

    return render(request, "pyyc/pyyc_main.html", context)

@staff_member_required
def update_data_view(request, **kwargs):
    result = update_data_task.delay()
    kwargs["task_id"] = result.task_id

    return redirect(reverse("pyyc:progress", kwargs=kwargs))

@staff_member_required
def run_forecasts(request, **kwargs):
    result = run_forecast_task.delay()
    kwargs["task_id"] = result.task_id

    return redirect(reverse("pyyc:progress", kwargs=kwargs))

@staff_member_required
def progress_view(request, **kwargs):
    if request.POST:
        return redirect(reverse("pyyc:main"))
    return render(request, "pyyc/progress_bar.html", context=kwargs)

@staff_member_required
def get_progress_view(request, **kwargs):
    result = AsyncResult(kwargs["task_id"])
    response_data = {
        "state": result.state,
        "details": result.info,
    }

    return JsonResponse(response_data)

class ForecastViewSet(ModelViewSet):
    """
    API endpoint that allows Yield Curve Forecasts to be viewed and edited.
    """
    queryset = Forecast.objects.all().order_by("-dataset__raw__last_date", "dataset")
    serializer_class = ForecastSerializer

class BOCGICForecastViewSet(ModelViewSet):
    """
    API endpoint that allows GIC Forecasts to be viewed and edited.
    """
    queryset = BOCGICForecast.objects.all().order_by("-last_date", "forecast")
    serializer_class = BOCGICForecastSerializer

class DatasetViewSet(ModelViewSet):
    """
    API endpoint that allows Datasets to be viewed and edited.
    """
    queryset = Dataset.objects.all().order_by("-raw__last_date")
    serializer_class = DatasetSerializer

class RAWViewSet(ModelViewSet):
    """
    API endpoint that allows RAW datasets to be viewed and edited.
    """
    queryset = RAW.objects.all().order_by("-last_date")
    serializer_class = RAWSerializer

class PrincipalComponentsViewSet(ModelViewSet):
    """
    API endpoint that allows Principal Components to be viewed and edited.
    """
    queryset = PC.objects.all().order_by("-raw__last_date")
    serializer_class = PrincipalComponentsSerializer

class CointegrationViewSet(ModelViewSet):
    """
    API endpoint that allows Cointegrations to be viewed and edited.
    """
    queryset = COINT.objects.all().order_by("-dataset__raw__last_date")
    serializer_class = CointegrationSerializer

class TechniqueViewSet(ModelViewSet):
    """
    API endpoint that allows Techniques to be viewed and edited.
    """
    queryset = TECH.objects.all()
    serializer_class = TechniqueSerializer

class VARViewSet(ModelViewSet):
    """
    API endpoint that allows VARs to be viewed and edited.
    """
    queryset = VAR.objects.all()
    serializer_class = VARSerializer

class VARMAViewSet(ModelViewSet):
    """
    API endpoint that allows VARMAs to be viewed and edited.
    """
    queryset = VARMA.objects.all()
    serializer_class = VARMASerializer

class VECMViewSet(ModelViewSet):
    """
    API endpoint that allows VECMs to be viewed and edited.
    """
    queryset = VECM.objects.all()
    serializer_class = VECMSerializer
