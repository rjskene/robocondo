import time
from datetime import datetime as dt, timedelta as td
from statistics import mean
import numpy as np
import pandas as pd
import math

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error as mse

from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.statespace.varmax import VARMAX
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen, select_order as order_vecm

from .analysis import PCA, CointAnal

class YieldCurveForecast:
    """
    Class for building yield curve forecasts from a dataframe of yield curve data

    1) Data confirmed in pandas dataframe format
        2) Allowed forecast formats: var, varma, vecm

    Attributes:
    pca = PCA object
    data = dataframe of pca
    n_diffs = order of difference of dataset
    nodiff_data = if n_diffs >= 1, must provide the undifferenced data
    """

    CONSTANTS = {
        "ALLOWED_MODELS": ["var", "varma", "vecm"],
        "DET_DICT": {
            "nc": "nc", "c": "ci", "ct": "colo"
        }
    }

    def __init__(self, data, external_data=None, n_diffs=0, nodiff_data=None):

        if not isinstance(data, PCA) and not isinstance(data, pd.DataFrame):
            raise TypeError(
                """
                data must be an object of the PCA class or a Pandas DataFrame
                """
            )
        if n_diffs == 0 and nodiff_data is not None:
            raise ValueError("If n_diffs equals 0, then nodiff_data should be None.")
        if n_diffs == 1 and nodiff_data is None:
            raise ValueError("""If n_diffs == 1, you must provide
                            the undifferenced data in nodiff_data""")
        if n_diffs > 1:
            raise ValueError("Order differences greater than 1 are not currently supported")

        if isinstance(data, PCA) and external_data is None:
            raise ValueError("""If PCA object is provided, external cannot be None.
                                If there is no external data, external should be empty DataFrame
                            """
            )

        self.external_data = external_data

        if isinstance(data, PCA):
            self.pca = data

            if external_data.empty:
                self.data = self.pca.df
            else:
                self.data = pd.concat([self.pca.df, external_data], axis=1)[1:]
        else:
            self.data = pd.concat([data, external_data], axis=1)[1:]
            self.pca = None

        self.n_diffs = n_diffs
        if self.n_diffs != 0:
            self.nodiff_data = nodiff_data

    def forecast(self, data=None, use_model="var", steps=360, order=(1,0), deterministic=None, seasons=12, freq="M", maxiter=1000):

        if type(order) != type(tuple()):
            raise TypeError(
                            """
                            Order must be of type Tuple;
                            if var is selected, input tuple with second order = 0;
                            i.e. var(1) order = (1,0), var(2) order = (2,0), etc.
                            """
            )
        if data is None:
            data = self.data

        start = time.time()

        if use_model == "var":
            results = self.var(data=data, order=order, freq=freq)
            yc_proj = results.forecast(data.values[:], steps=steps)
        elif use_model == "varma":
            results = self.varma(data=data, order=order, freq=freq)
            yc_proj = results.forecast(steps=steps).values
        elif use_model == "vecm":
            """
            If alpha is included in predict it will provide confidence intervals
            """
            if deterministic:
                deterministic = self.CONSTANTS["DET_DICT"][deterministic]
            else:
                raise ValueError("You must input value for deterministic")

            results = self.vecm(data=data,
                                order=order,
                                deterministic=deterministic,
                                seasons=seasons, freq="M"
            )
            yc_proj = results.predict(steps=steps)
        else:
            raise ValueError("{} are the only allowed model types"
                             .format(", ".join(self.CONSTANTS["ALLOWED_MODELS"]))
            )

        end = time.time()
        self.process_time = end - start
        df_proj = self.projected_df(yc_proj=yc_proj, steps=steps)

        return df_proj, yc_proj, results

    def train(self, test_len=60, data=None, use_model="var", order=(1,0), deterministic=None, seasons=12, freq="M", maxiter=1000):
        """
        Train the model over slices of the dataset. Number of slices is determined
        by test_len

        Parameters
        -------
        data, use_model, order, deterministic, freq, maxiter: all as described in forecast() method
        test_len: length of each training period

        Returns
        -------
        total_rmse: Total Root Mean Squared Error (RMSE) across all variables for last 3 datasets combined
        set_rmses: list of RMSEs for each train dataset used; will show large errors
                    for earlier train sets in some regression techniques
        df_projs: dict of tuples of two DataFrames; first DF is actual yield cureve,
                second DF is projected yield curve; if regression method throws exception
                the exception is stored instead
        """
        if data is None:
            data = self.data

        max_len = len(self.data) - test_len
        min_len = max_len % test_len
        first_len = min_len + test_len if min_len < test_len else min_len

        if use_model == "vecm":
            first_len = first_len + test_len if seasons > first_len / 2 else first_len

        set_mses = []
        set_rmses = []
        df_trains = {}

        for i in range(first_len - 1, max_len + 1, test_len):
            train_data = data[ : i]
            test_data = data[i + 1: i + 1 + test_len]

            try:
                test_proj, yc_proj, _1 = self.forecast(data=train_data, use_model=use_model, steps=test_len,
                                    order=order, deterministic=deterministic,
                                    seasons=seasons, freq=freq, maxiter=1000)
                test_proj.index = test_data.index

                test_act = self.projected_df(yc_proj=test_data.values, steps=test_len)
                test_act.index=test_data.index

                df_trains[i + 1] = (test_act, test_proj)

                mses = []
                for column in test_proj:
                    mses.append(mse(test_act[column], test_proj[column]))

                set_mse = mean(mses)

                set_mses.append(set_mse)
                set_rmse = math.sqrt(set_mse)
                set_rmses.append(set_rmse)

            except Exception as e:
                print ("""Training Exception at Step {}: {}.
                        See YieldCurveForecast.train method""".format(i, str(e))
                )
                df_trains[i + 1] = e

        total_rmse = math.sqrt(mean(set_mses[-3:]))

        return total_rmse, set_rmses, df_trains

    def var(self, data, order=(1,0), freq="M", maxiter=1000):
        """
        Fits a var structure to Data

        data: clean Dataframe resulting
        Order: p variable (number of correlated time lags to regress); q = 0
        freq: frequency of time series; should be inferred automatically from Dataframe
        """

        self.var_model = VAR(data, freq=freq)
        var_fit = self.var_model.fit(order[0])

        return var_fit

    def varma(self, data, order=(1,0), freq="M", maxiter=1000):
        """
        Fits a varma structure to Principal Components (PCA)

        df_PCA: clean Dataframe resulting from PCA output from statsmodels
        Order: p variable (number of correlated time lags to regress)
        Order: q variable (nuumber of correlated error lags to regress)
        freq: frequency of time series; should be inferred automatically from Dataframe
        """
        varma = VARMAX(data, order=order, dates=data.index, freq=freq)
        varma_fit = varma.fit(maxiter=1000, disp=False)

        return varma_fit

    def vecm(self, data, order=(1,0), deterministic="ci", seasons=12, coint_rank=None, freq="M"):
        """
        Fits a vecm structure to Principal Components (PCA)

        df_PCA: clean Dataframe resulting from PCA output from statsmodels
        Order: p variable (number of correlated time lags to regress)
        Order: q variable (nuumber of correlated error lags to regress)
        freq: frequency of time series; should be inferred automatically from Dataframe
        """

        vecm = VECM(
                    data, k_ar_diff=order[0],
                    deterministic=deterministic,
                    seasons=seasons, coint_rank=coint_rank, freq=freq
        )
        vecm_fit = vecm.fit()

        return vecm_fit

    def projected_df(self, yc_proj, steps, dates=None):
        """
        Build DataFrame of forecast yield curve plus any external variables
        If there the data is first order differenced, the use diff_recast
        If data is not differenced, check if PCA object provided
        If PCA object provided, principal components must be transformed to yields
        Then external variables are attached to the yields

        Parameters
        -----------
        > yc_proj:  numpy array; derived from statsmodels predict() or forecast() methods
        > steps:    integer; number of periods to forecast
        > dates:    pandas Date range; dates for the projection period
                    > if dates is None, dates are calculated from first period of self.data and steps

        Returns
        --------
        > df_proj:  pandas DataFrame; dataframe of forecasted yields and external variables
        """
        if isinstance(dates, type(None)):
            first_date = pd.to_datetime(self.data.tail(1).index[0]) \
                            + pd.DateOffset(months=1)
            rng = pd.date_range(start=first_date, periods=steps, freq="M")
        else:
            rng = dates
        if self.n_diffs == 1:
            df_proj = self.diff_recast(yc_proj, rng)
        else:
            # NEED TO INCLUDE ALPHA FOR VECM!!!!!
            columns = self.data.columns
            if isinstance(self.pca, PCA):
                if self.external_data is None or self.external_data.empty:
                    yc_proj = self.pca.pca.inverse_transform(yc_proj)
                    columns = self.pca.orig_data.columns
                else:
                    data = self.pca.pca.inverse_transform(yc_proj[ : , :self.pca.n_components])
                    yc_proj = np.hstack((data, yc_proj[ : , self.pca.n_components: ]))
                    columns = self.pca.orig_data.columns.tolist() + self.external_data.columns.tolist()

            df_proj = pd.DataFrame(data=yc_proj, index=rng, columns=columns)

        df_proj.index.name = "Date"

        return df_proj

    def diff_recast(self, yc_proj, rng):
        """
        Convert projected data from differenced data to absolute data
        1) Create new DF whose first row is last row of the undifferenced dataset
        2) if yc_proj is Principal Components, convert to raw data using inverse_transform;
            this gives the differenced raw data
        3) For each period in the diff raw data, add that row to the prior period
            of the undiff data; this gives the non-diff data for the current period
        4) Remove the first period
        5) Add Datetimeindex
        """
        recast = np.array([self.nodiff_data.iloc[-1]])

        if isinstance(self.pca, PCA):
            if self.external_data is None or self.external_data.empty:
                yc_proj = self.pca.pca.inverse_transform(yc_proj)
            else:
                data = self.pca.pca.inverse_transform(yc_proj[ : , :self.pca.n_components])
                yc_proj = np.hstack((data, yc_proj[ : , self.pca.n_components: ]))
        x = 0
        for row in yc_proj:
            recast_row = recast[x] + row
            recast = np.vstack([recast, recast_row])
            x += 1

        recast = recast[1:]
        columns = self.nodiff_data.columns
        df_proj = pd.DataFrame(data=recast, index=rng, columns=columns)

        return df_proj

class GICForecast:
    """
    Create GIC Forecast
    """

    def __init__(self, df_yields, df_bocgic, df_proj):
        self.cols = ["one_year", "two_year", "three_year", "four_year", "five_year", "rate"]
        self.df_yields = df_yields
        self.df_bocgic = df_bocgic
        self.df_proj = df_proj

    def forecast(self):
        arr_proj = np.zeros(shape=(len(self.cols), len(self.df_proj)))
        regrs = {}
        for i, col in enumerate(self.cols):
            regrs[col] = self.regression(self.df_yields[[col]], self.df_bocgic[[col]])

            arr_proj[i] = self.predict(regrs[col], self.df_proj[[col]])

        arr_proj = np.swapaxes(arr_proj, 0, 1)

        self.df_proj_gic = pd.DataFrame(data=arr_proj, index=self.df_proj.index, columns=self.cols)
        self.df_proj_gic = self.df_proj_gic[["rate", "one_year", "two_year", "three_year", "four_year", "five_year"]]
        
        return self.df_proj_gic

    def regression(self, yields, bocgic):
        df_concat = pd.concat([yields, bocgic], axis=1)
        df_concat = df_concat.dropna()
        values = np.swapaxes(df_concat.values, 0, 1)
        x = values[0].reshape(-1, 1)
        y = values[1].reshape(-1, 1)
        regr = LinearRegression()
        regr.fit(x, y)

        return regr

    def predict(self, regr, projected):
        return regr.predict(projected.values.reshape(-1, 1)).flatten()
