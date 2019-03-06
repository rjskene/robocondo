from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, FactorRange, Range1d, \
                    SingleIntervalTicker, LinearAxis, DatetimeTickFormatter, \
                    NumeralTickFormatter, Legend
from bokeh.models.sources import AjaxDataSource
from bokeh.palettes import Blues, Category20b, Category20c, Pastel1, Set3, small_palettes, brewer
from bokeh.transform import factor_cmap, dodge
from bokeh.core.properties import value as val

from bokeh.embed import components
from bokeh.embed import server_session
from bokeh.util import session_id

def bank_chart(forecast):
    """Reserve Fund Total Chart"""
    data = {
            "Date": [row["month"].strftime("%b %Y") for row in forecast][:36],
            "Bank Balance": [row["bank_balance"] for row in forecast][:36]
    }
    p = figure(x_range=data["Date"], plot_height=250, x_axis_type="datetime", tools="")
    p.line(x=data["Date"], y=data["Bank Balance"], color=Blues[3][1], line_width=3)
    p.yaxis.formatter = NumeralTickFormatter(format="$1,000")
    p.xaxis.major_label_overrides = {
        i: row["month"].strftime("%b %Y") for i, row in enumerate(forecast) if i < 36
    }
    dct = {}
    dct["script"], dct["div"] = components(p)

    return dct

def alloc_chart(forecast):
    data = {
            "Date": [row["month"].strftime("%b %Y") for row in forecast][:36],
            "Term 1": [row["term_1"] for row in forecast][:36],
            "Term 2": [row["term_2"] for row in forecast][:36],
            "Term 3": [row["term_3"] for row in forecast][:36],
            "Term 4": [row["term_4"] for row in forecast][:36],
            "Term 5": [row["term_5"] for row in forecast][:36]
    }
    invmts = [x for x in data.keys() if x !="Date"]
    p = figure(x_range=data["Date"], plot_height=250, x_axis_type="datetime",
               toolbar_location=None, tools=""
    )
    p.vbar_stack(invmts, x="Date", width=0.9, color=Set3[len(invmts)], source=data,
                 legend=[val(x) for x in invmts]
    )
    p.y_range.start = 0
    p.x_range.range_padding = 0.1
    p.xgrid.grid_line_color = None
    p.xaxis.major_label_overrides = {
        i: row["month"].strftime("%b %Y") for i, row in enumerate(forecast) if i < 36
    }
    p.yaxis.formatter = NumeralTickFormatter(format="$1,000")
    p.legend.location = "top_right"
    p.legend.orientation = "horizontal"

    dct = {}
    dct["script"], dct["div"] = components(p)

    return dct

def contsexps_chart(forecast, annual_conts, annual_exps):
    """CONTRIBUTIONS & EXPENDITURES CHART"""
    data = {
            "Date": [row["month"].strftime("%b %Y")[4:] for i, row in enumerate(forecast) if (i + 1) % 12 == 0][:5],
            "Contributions": annual_conts[:5],
            "Expenditures": annual_exps[:5]
    }
    source = ColumnDataSource(data=data)
    p = figure(x_range=data["Date"], plot_height=250, toolbar_location=None, tools="")
    p.vbar(x=dodge("Date", -0.25, range=p.x_range), top="Contributions", width=0.2, source=source,
           color=Blues[3][0], legend=val("Contributions")
    )
    p.vbar(x=dodge("Date",  0.0,  range=p.x_range), top="Expenditures", width=0.2, source=source,
           color=Blues[3][1], legend=val("Expenditures")
    )

    p.x_range.range_padding = 0.1
    p.xgrid.grid_line_color = None
    p.yaxis.formatter = NumeralTickFormatter(format="$1,000")
    p.legend.location = "top_right"
    p.legend.orientation = "vertical"

    script, div = components(p)

    dct = {}
    dct["script"] = script
    dct["div"] = div

    return dct

def total_chart(forecast, annual_exps):
    """Reserve Fund Total Chart"""
    data = {
            "Date": [row["month"].strftime("%Y") for i, row in enumerate(forecast) if (i + 1) % 12 == 0][:30],
            "Total": [row["closing_balance"] / 1000000 for i, row in enumerate(forecast) if (i + 1) % 12 == 0][:30],
            "Expenditures": [exp / 1000000 for exp in annual_exps]
    }
    p = figure(x_range=data["Date"], plot_height=250, x_axis_type="datetime", toolbar_location=None, tools="")
    p.vbar(x=data["Date"], top=data["Expenditures"], color=Blues[3][1], width=0.5)
    p.line(x=data["Date"], y=data["Total"], color=Blues[3][0], line_width=3)
    p.xaxis.major_label_overrides = {
        i: date for i, date in enumerate(data["Date"])
    }

    p.yaxis.axis_label = "(in millions)"
    p.yaxis.formatter = NumeralTickFormatter(format="$0")
    script, div = components(p)

    dct = {}
    dct["script"] = script
    dct["div"] = div

    return dct
