import time
from datetime import datetime as dt, timedelta as td
import pandas as pd

from pyyc.models import HistoricalYieldCurve as HYC, HistoricalOvernightRate as HOR, \
                        InflationRate as INFR, OutputGap as GAP

def fill_nans(df, cols=["inflation", "output_gap"]):
    for col in cols:
        last_date = None
        for date, row in df.iloc[::-1].iterrows():
            if not df.isnull().loc[date, col]:
                last_date = date
                fwd_value = row[col]
                break

        for date, row in df.loc[last_date:, :].iterrows():
            if date != last_date:
                df.loc[date, col] = fwd_value

    return df

def make_frame(model, excluded=["id", "date_added", "date_modified"], filter=False, **kwargs):
    """
    Make dataframe from pyyc data Model
    Dataframe is more flexible for resampling and morphing
    Exclude unnecessary model fields, set date as index
    """
    if filter:
        values = model.objects.filter(**kwargs).values()
    else:
        values = model.objects.all().values()
    df = pd.DataFrame(list(values))

    df.set_index("date", inplace=True)
    df.index = pd.to_datetime(df.index, infer_datetime_format=True)
    cols = [col for col in df.columns if col not in excluded]
    df = df[cols]

    return df

def make_combined_frame():
    """
    Combine multiple django models into single dataframe
    Each model / dataset has its own shaping requirements
    HYC is the date restriction, so the first date of HYC is the minimum date
    for each of the other models.
    HYC is daily rates so needs to be upsampled to monthly
    GAP is quarterly so needs to be downsampled to monthly
    Returns the combined Dataframe
    """
    models = {"HOR": HOR, "HYC": HYC, "INFR": INFR, "GAP": GAP}

    frames = {key: make_frame(val) for key, val in models.items()}
    frames["HOR"]= frames["HOR"].loc[frames["HYC"].index[0]:, :].resample("M").last()
    frames["HYC"] =  frames["HYC"].resample("M").mean()
    frames["INFR"] = frames["INFR"].loc[frames["HYC"].index[0]:, :]
    frames["GAP"] = frames["GAP"].resample("M").interpolate().loc[frames["HYC"].index[0]:, :]

    concat_frames = [frame for key, frame in frames.items()]

    df_combined = pd.concat(concat_frames, axis=1).copy()
    df_combined.dropna(how="all")

    df_combined = df_combined.dropna(thresh=10)
    fill_nans(df_combined)

    if df_combined.isnull().values.any():
        raise ValueError("The combined dataframe cannot have any null values")

    return df_combined
