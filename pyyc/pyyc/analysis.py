import time
from datetime import datetime as dt, timedelta as td
import numpy as np
import pandas as pd

from sklearn.decomposition import PCA as SKLEARNPCA

from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen

class PCA:
    """
    Class for finding principal components of a yield curve dataset
    """

    def __init__(self, data, n_components=3):
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Data structure must be Pandas Dataframe")
        else:
            self.df_data = data

        self.orig_data = data
        self.n_components = n_components
        self.pca, self.df = self.pca()
        self.explained = self.pca.explained_variance_ratio_.tolist()

    def pca(self):
        # calculate Principal components for input variables
        pca = SKLEARNPCA(n_components=self.n_components, copy=True, whiten=False)
        pca.fit(self.df_data)
        df = pd.DataFrame(pca.transform(self.df_data), columns=["PC {}".format(i+1) for i in range(self.n_components)])
        df.index = self.df_data.index

        return pca, df

class CointAnal:

    DET_DICT = { "nc": -1, "c": 0, "ct": 1, "ctt": 1}

    def __init__(self, data, crit="5%", maxlag=36, reg="c", autolag='AIC', k_ar_diff=36):
        """
        Parameters
        -------

        ***FOR ADF TEST***
        crit: critical value threshold for rejecting null of ADF Test
        reg: regression structure of cointegration for ADF
                "c" : constant only (default)
                "ct" : constant and trend
                "ctt": constant, and linear and quadratic trend
                "nc" : no constant, no trend
        autolag: autolag process for ADF Test

        ***FOR JOHANSEN TEST***
        k_ar_diff: number of correlation lags
        """

        if type(data) != type(pd.DataFrame()):
            raise TypeError("Data structure must be Pandas Dataframe")

        self.data = data

        # inputs for ADF Test
        self.crit = crit
        self.maxlag = maxlag
        self.reg = reg
        self.autolag = autolag

        # outputs for ADF Test
        self.adf_results = self.unitroot_test(data=self.data)
        self.any_unitroots = self.is_unitroot(results=self.adf_results)
        self.n_diffs = self.no_roots()
        data_noroots = self.getdata_noroots()

        # inputs for Johanen test for cointegration
        self.k_ar_diff = k_ar_diff

        # outputs for Johansen Test for cointegration
        self.jres = self.get_johansen(self.data)

    def getdata_noroots(self):

        diff_data = self.data
        for x in range(self.n_diffs):
            diff_data = diff_data.diff().dropna()

        return diff_data

    def no_roots(self):
        """
        1) Test if data set has unit roots
        2) If yes, take first difference
        3) Repeat until no unit roots

        Parameters
        -------
        self.data

        Returns
        -------
        n_diffs: number of differences required to eliminate unit roots
        """

        diff_data = self.data
        n_diffs = 0
        while True:
            results = self.unitroot_test(diff_data)

            # if there are any roots, take first difference of data
            # if diff = self.data, then this is the first pass and self.data must differenced
            # if diff != self.data, then this is 2/3/4 etc. pass and diff must differenced
            if self.is_unitroot(results):
                if diff_data.equals(self.data):
                    diff_data = self.data.diff().dropna()
                else:
                    diff_data = diff_data.diff().dropna()
                n_diffs += 1
            else:
                break

        return n_diffs

    def is_unitroot(self, results):
        # create list of boolean results; if any column has a unit root, return True
        return any([v[0] for k,v in results.items()])

    def unitroot_test(self, data):
        """
        Test if each column in data has a unit root at specific critical value

        Parameters
        -------
        maxlag: maximum number of lag periods to consider for test

        Returns
        -------
        results: dictionary with key=column name,
                                 value=tuple of (Boolean, critical value, adf result)
        if Boolean is True then the column is non-stationary at specified critical value
        """
        results = {}
        for column in data:
            results[column] = self.augdicfull(col=data[column])

        return results

    def augdicfull(self, col):
        """
        Augmented Dickey Fuller test
        null hypothesis is that the input vector has a Unit Root (i.e. is non-stationary)

        Parameters
        ----------
        col: column(vector) of Yields or Principal Components

        Returns
        -------
        boolean: bool
            If test statistic < critical value, reject null; boolean = False; No Unit Root
            If test statistic > crictical value, do NOT reject null; boolean = True; Unit Root
        """

        boolean = False

        adf = adfuller(col, maxlag=self.maxlag, regression=self.reg, autolag=self.autolag)
        if(adf[0] < adf[4][self.crit]):
            pass
        else:
            boolean = True

        return boolean, self.crit, adf

    def get_johansen(self, data):
        """
        Get the cointegration vectors at highest level of significance
        given by the trace statistic test.
        If no cointegration vectors, return coint_rank of 0

        Parameters
        ----------
        Deterministic: is either -1,0,1; values derived from self.reg & DET_DICT
                        -1: no deterministic term
                         0: constant term
                         1: linear term
        k_ar_diff: number of correlation lags; derived from self
        """
        SIGNF_DICT = {0: "90%", 1: "95%", 2: "99%"}
        N, l = data.shape
        jres = coint_johansen(data, self.DET_DICT[self.reg], self.k_ar_diff)
        trstat = jres.lr1                       # trace statistic
        tsignf = jres.cvt                       # critical values

        if not self.any_unitroots:
            # if there are no unit roots, Cointegration analysis is not useful
            # therefore, values are set to none
            jres.coint_rank = None
            jres.signf_level = None
        else:
            for x in range(l):
                for y in range(2,-1,-1):
                    if trstat[x] > tsignf[x, y]:
                        coint_rank = x + 1

                    try:
                        jres.coint_rank = coint_rank
                        jres.signf_level = SIGNF_DICT[y]
                    except UnboundLocalError:
                        if y == 2:
                            jres.coint_rank = 0
                            jres.signf_level = "Null Significance"
                        else:
                            pass

            jres.evec_ranks = jres.evec[:, :jres.coint_rank]

        return jres
