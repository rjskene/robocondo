import time
from datetime import datetime as dt, timedelta as td
import pandas as pd
from urllib.request import urlopen, Request, urlretrieve
from bs4 import BeautifulSoup as bs

import zipfile
import quandl

from django.db import transaction

from robocondo.global_helpers import get_or_none
from pyyc.models import HistoricalYieldCurve as HYC, HistoricalOvernightRate as HOR, \
                        InflationRate as INFR, OutputGap as GAP, Cointegration as COINT, \
                        VAR, VARMA, VECM, Technique as TECH, BOCGICs

from urllib.request import urlopen, Request
from bs4 import BeautifulSoup as bs

quandl.ApiConfig.api_key = "z3RrGrs1QX8nyRGSZPmh"

HYC_KEYS = {
                " ZC025YR": "three_month",
                " ZC050YR": "six_month",
                " ZC100YR": "one_year",
                " ZC200YR": "two_year",
                " ZC300YR": "three_year",
                " ZC400YR": "four_year",
                " ZC500YR": "five_year",
                " ZC700YR": "seven_year",
                " ZC1000YR": "ten_year",
                " ZC2500YR": "twenty_five_year"
}

@transaction.atomic
def update_data():
    print ("Initialize update data...")
    # update_yc_quandl()
    update_yc_request()
    update_bankrate()
    update_inf()
    update_gap()
    update_bocgic()
    print ("Update Complete!")

def update_yc_quandl():
    cols = HYC_KEYS
    last_date = HYC.objects.latest("date").date

    concat_frames = []
    for keys, values in cols.items():
            concat_frames.append(quandl.get("BOC/{}".format(keys[1:])).loc[last_date:])
    df = pd.concat(concat_frames, axis=1)[1:]
    df.columns = cols.values()

    for idx, row in df.iterrows():
        new_hyc = HYC()
        setattr(new_hyc, "date", idx)
        for col, value in row.iteritems():
            setattr(new_hyc, col, value)
        new_hyc.save()

def update_yc_request():
    outfilename = "test.xls"

    last_date = HYC.objects.latest("date").date
    current_date = dt.today().strftime("%Y-%m-%d")

    url_of_file = "https://www.bankofcanada.ca/stats/results/csv?lookupPage=lookup_yield_curve.php&startRange=1986-01-01&searchRange=&dFrom={}&dTo={}&submit=Submit".format(last_date, current_date)
    urlretrieve(url_of_file, outfilename)

    df = pd.read_csv(outfilename)
    df.set_index("Date", inplace=True)
    df.index = pd.to_datetime(df.index)
    df = df[list(HYC_KEYS.keys())]
    df.rename(columns=HYC_KEYS, inplace=True)

    df = df.loc[~(df==" na").all(axis=1)]

    df = df.astype(float)
    # iterate through each new row; check if date in HYC and, if not, save each column
    for date, row in df.iterrows():
        if not get_or_none(HYC, date=date):
            new_hyc = HYC()
            setattr(new_hyc, "date", date)
            for col, value in row.iteritems():
                setattr(new_hyc, col, value)
            new_hyc.save()

def update_bankrate():
    last_date = HOR.objects.latest("date").date
    df = quandl.get("BOC/V39079").loc[last_date:][1:]

    for date, rate in df.iterrows():
        if not get_or_none(model=HOR, date=date):
            HOR.objects.create(date=date, rate=rate/100)

def update_inf():
    df = quandl.get("RATEINF/INFLATION_CAN")
    for date, rate in df.iterrows():
        if not get_or_none(model=INFR, date=date):
            INFR.objects.get_or_create(date=date, inflation=rate/100)

def update_gap():
    gap_url = "https://www.bankofcanada.ca/rates/indicators/capacity-and-inflation-pressures/product-market-definitions/product-market-historical-data/"

    headers = {}
    headers['User-Agent'] ='Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
    req = Request(gap_url, headers=headers)
    uClient = urlopen(req)
    page = uClient.read()
    uClient.close()

    soup = bs(page, "html.parser")
    table = soup.find("tbody", {"class": "bocss-table__tbody"})
    rows = table.find_all("tr")

    dates = [row.contents[0].text for row in rows]
    values = [row.contents[2].text for row in rows]
    cols = ["output_gap"]

    df = pd.DataFrame(index=dates, data=values, columns=cols)
    print (df)
    df.index = pd.to_datetime(df.index).to_period("M").to_timestamp("M")
    values = make_values(df)
    for record in values:
        if not get_or_none(model=GAP, date=record["date"]):
            GAP.objects.get_or_create(date=record["date"], output_gap=record["output_gap"])

def update_bocgic(one_time=False):
    gic1 = "BOC/V121771"
    gic3 = "BOC/V121772"
    gic5 = "BOC/V121773"
    prime = "BOC/V122495"

    rates = [gic1, gic3, gic5, prime]
    dfs = [quandl.get(rate) for rate in rates]
    df = pd.concat(dfs, axis=1)
    df = df / 100

    if not one_time:
        last_date = BOCGICs.objects.latest("date").date
        df = df.loc[last_date: ][1: ]

    df.reset_index(inplace=True)
    df.columns = [f.name for f in BOCGICs._meta.get_fields() if f.name not in ["id", "date_added", "date_modified"]]
    BOCGICs.objects.bulk_create(BOCGICs(**vals) for vals in df.to_dict("records"))

    return df

def make_values(df):
    """
    1) Convert dataframe to list of dictionaries for each record
    2) Add date to each dictionary from dataframe index
    """
    values = df.to_dict("records")

    for idx, row in enumerate(values):
        row["date"] = df.index[idx].to_pydatetime()

    return values

"""
DO NOT USE
MODULE USED FOR ONE-TIME UPLOAD OF VARIOUS DATA
"""

YC_PATH = "/code/pyyc/data/upload_data/CADYIELDCURVE.csv"
IR_PATH = "/code/pyyc/data/upload_data/CADBANKRATE.csv"
INF_PATH = "/code/pyyc/data/upload_data/CAD_INFLATION.csv"
GAP_PATH = "/code/pyyc/data/upload_data/OUTPUT_GAP.csv"

def historical_bulkcreate():
    """
    Function designed for single use
    Upload all existing data into django models
    Run from manage.py shell
    """
    df_cad, yc_values = yc_upload(YC_PATH)
    df_cadrate, ir_values = overnight_upload(IR_PATH)
    df_inf, inf_values = inflation_upload(INF_PATH)
    df_gap, gap_values = outputgap_upload(GAP_PATH)

    HYC.objects.bulk_create(objs=(HYC(**vals) for vals in yc_values))
    HOR.objects.bulk_create(objs=(HOR(**vals) for vals in ir_values))
    INFR.objects.bulk_create(objs=(INFR(**vals) for vals in inf_values))
    GAP.objects.bulk_create(objs=(GAP(**vals) for vals in gap_values))

    return df_cad, df_cadrate, df_inf, df_gap

def yc_upload(path):
    """
    Upload existing data from .csv
    Clean data, convert to list of dicts
    """
    df_cad = pd.read_csv(path)
    df_cad.set_index("Date", inplace=True)

    df_cad.index = pd.to_datetime(df_cad.index, format="%d/%m/%y")
    cols =  [
                        " ZC025YR",
                        " ZC050YR",
                        " ZC100YR",
                        " ZC200YR",
                        " ZC300YR",
                        " ZC400YR",
                        " ZC500YR",
                        " ZC700YR",
                        " ZC1000YR",
                        " ZC2500YR",
    ]
    df_cad = df_cad[cols]
    df_cad.rename(columns={
                        " ZC025YR": "three_month",
                        " ZC050YR": "six_month",
                        " ZC100YR": "one_year",
                        " ZC200YR": "two_year",
                        " ZC300YR": "three_year",
                        " ZC400YR": "four_year",
                        " ZC500YR": "five_year",
                        " ZC700YR": "seven_year",
                        " ZC1000YR": "ten_year",
                        " ZC2500YR": "twenty_five_year"
                    },
                    inplace=True
    )
    df_cad = df_cad[~df_cad.eq(" na")]
    df_cad.dropna(inplace=True)
    df_cad = df_cad.astype(float)

    values = make_values(df_cad)

    return df_cad, values

def overnight_upload(path):
    """
    Upload existing data from .csv
    Clean data, convert to list of dicts
    """
    df_cadrate = pd.read_csv(path, encoding = "ISO-8859-1")
    yrs = [i for i in range(1935, 2018)]
    data = df_cadrate.columns[0].split()[39:]
    for index, row in df_cadrate.iterrows():
        data += row[0].split()[39:]
    yrs = list(map(str, yrs))
    data = [i for i in data if i not in yrs]
    data = list(map(float, data))
    data += [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.75, 1.75, 1.75, 1.75]
    date_index = pd.date_range(start="1935-1", end="2018-11", freq="M")
    df_cadrate = pd.DataFrame(data=data, index=date_index)
    df_cadrate.columns = ["rate"]
    df_cadrate.index.name = "date"
    df_cadrate /= 100

    values =  make_values(df_cadrate)

    return df_cadrate, values

def inflation_upload(path):
    df_inf = pd.read_csv(path, encoding="ISO-8859-1")
    df_inf = df_inf.loc[(df_inf["UOM"] == "2002=100") &
               (df_inf["Products and product groups"] == "All-items") &
               (df_inf["GEO"] == "Canada")
    ]
    cols =  ["REF_DATE", "VALUE"]
    df_inf = df_inf[cols]
    df_inf.rename(columns={"REF_DATE": "date", "VALUE": "inflation"}, inplace=True)
    df_inf.set_index("date", inplace=True)
    df_inf.index = pd.date_range(start="1914-1", end="2018-10", freq="M")
    df_inf = df_inf.pct_change(12).dropna()

    values = make_values(df_inf)

    return df_inf, values

def outputgap_upload(path):
    df_gap = pd.read_csv(path)
    df_gap.rename(columns={"Quarter": "date",
                           "Output gap (Extended multivariate filter) (%)": "output_gap"},
                  inplace=True
    )
    cols =  [
                        "date",
                        "output_gap",
    ]
    df_gap = df_gap[cols]
    df_gap = df_gap.loc[1:]
    df_gap.set_index("date", inplace=True)
    df_gap = df_gap.iloc[::-1]
    df_gap.index = pd.date_range(start="1981-3", end='2018-10', freq="3M")
    df_gap = df_gap / 100

    values = make_values(df_gap)

    return df_gap, values

def create_techniques():
    ps = [1, 12, 24, 36, 48, 60]
    qs = [1, 2, 3]
    seasons = [12, 24, 36, 48]
    dets = [choice[1] for choice in COINT.DET.choices()]

    for p in ps:
        VAR.objects.create(p=p)
    for var_obj in VAR.objects.all():
        TECH.objects.create(var=var_obj)

    for p in ps:
        for q in qs:
            VARMA.objects.create(p=p, q=q)
    for varma_obj in VARMA.objects.all():
        TECH.objects.create(varma=varma_obj)

    for p in ps:
        for season in seasons:
            for det in dets:
                VECM.objects.create(p=p, seasons=season, deterministic=det)
    for vecm_obj in VECM.objects.all():
        TECH.objects.create(vecm=vecm_obj)
