import time
import socket
from datetime import datetime as dt, date
from dateutil.relativedelta import relativedelta
import pandas as pd
from pandas.testing import assert_frame_equal
import numpy as np

import quandl

from django.db import IntegrityError
from django.utils import timezone
from django.test.utils import override_settings
from django.test.client import Client
from django.contrib.auth.models import User
from django.test import TestCase, tag, LiveServerTestCase

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from condo.models import Condo
from condo.helpers import condo_short_name

from pyondo.pyondo import Pyondo

from condo.models import Condo
from reservefundstudy.models import Study, Contributions, Expenditures
from investmentplan.models import Plan, Forecast
from investmentplan.helpers import int_to_date, find_date
from investmentplan.converter import Converter

from robocondo.global_helpers import get_or_none
from condo.tests.factories import CondoFactory, BankAccountsFactory as BAFactory, \
                    AccountBalanceFactory as ABFactory, InvestmentsFactory as InvmtsFactory
from investmentplan.tests.factories import PlanFactory
from reservefundstudy.tests.factories import StudyFactory, ContributionsFactory as ContFactory, \
            ExpendituresFactory as ExpFactory, cont_kwargs, exp_kwargs
from pyyc.models import HistoricalYieldCurve as HYC, HistoricalOvernightRate as HOR, \
                        InflationRate as INFR, OutputGap as GAP, RAW, BOCGICs, \
                        PrincipalComponents as PC, Dataset, Cointegration as COINT, Technique as TECH, \
                        VAR, VARMA, VECM, Forecast
from pyyc.data.update import yc_upload, overnight_upload, inflation_upload, outputgap_upload, \
                        YC_PATH, IR_PATH, INF_PATH, GAP_PATH, historical_bulkcreate, \
                        create_techniques, make_values, update_gap, update_inf, update_bankrate, \
                        HYC_KEYS, update_data, update_bocgic
from pyyc.data.combine import make_combined_frame, make_frame
from pyyc.pyyc.analysis import PCA, CointAnal
from pyyc.pyyc.main import PYYC
from pyyc.pyyc.forecast import YieldCurveForecast, GICForecast

class UploadDataTests(TestCase):
    fixtures = ["users.json"]

    @classmethod
    def setUpTestData(self):
        self.df_cad, self.df_cadrate, self.df_inf, self.df_gap = historical_bulkcreate()

    @override_settings(
        DEBUG=True,
    )
    def test_yield_curve_data_upload(self):
        hyc = HYC.objects.all().values()
        excluded = ["id", "date_added", "date_modified"]
        field_names = [f.name for f in HYC._meta.get_fields() if f.name not in excluded]

        for idx, row in enumerate(hyc):
            for name in field_names:
                if name == "date":
                    self.assertEquals(row[name], self.df_cad.iloc[idx].name.to_pydatetime().date())
                else:
                    self.assertEquals(row[name], self.df_cad.iloc[idx][name])

    def test_cad_overnight_rate_data_upload(self):

        hor = HOR.objects.all()

        for idx, row in enumerate(hor):
            self.assertEquals(row.date, self.df_cadrate.iloc[idx].name.to_pydatetime().date())
            self.assertEquals(round(row.rate, 4), round(self.df_cadrate.iloc[idx]["rate"], 4))

    def test_inflation_rate_data_upload(self):
        infr = INFR.objects.all()

        for idx, row in enumerate(infr):
            self.assertEquals(row.date, self.df_inf.iloc[idx].name.to_pydatetime().date())
            self.assertEquals(round(row.inflation, 5), round(self.df_inf.iloc[idx]["inflation"], 5))

    def test_output_gap_data_upload(self):
        gap = GAP.objects.all()

        for idx, row in enumerate(gap):
            self.assertEquals(row.date, self.df_gap.iloc[idx].name.to_pydatetime().date())
            self.assertEquals(round(row.output_gap, 4), round(self.df_gap.iloc[idx]["output_gap"], 4))

    def test_create_regression_technique_records(self):
        create_techniques()

        techniques = TECH.objects.all()
        for technique in techniques:
            if technique.var:
                self.assertEqual(technique.varma, None)
                self.assertEqual(technique.vecm, None)
            if technique.varma:
                self.assertEqual(technique.var, None)
                self.assertEqual(technique.vecm, None)
            if technique.vecm:
                self.assertEqual(technique.var, None)
                self.assertEqual(technique.varma, None)

class CombineDataTests(TestCase):
    # fixtures = ["yields.json"]

    @classmethod
    def setUpTestData(self):
        historical_bulkcreate()
        update_bocgic(one_time=True)


    def test_combine_data_from_historical_models(self):

        df_combined = make_combined_frame()
        update_data()

class TechniqueModelTests(TestCase):
    # fixtures = ["yields.json"]

    @classmethod
    def setUpTestData(self):
        historical_bulkcreate()
        update_bocgic(one_time=True)
        update_data()

        # Variables for Cointegration
        root_crit = "5%"
        self.det = "c"
        self.p = 36

        self.var_obj = VAR.objects.create(p=self.p)
        self.varma_obj = VARMA.objects.create(p=1, q=1)
        self.vecm_obj = VECM.objects.create(p=self.p, seasons=24, deterministic=self.det)

        self.tech_var = TECH.objects.create(var=self.var_obj)
        self.tech_varma = TECH.objects.create(varma=self.varma_obj)
        self.tech_vecm = TECH.objects.create(vecm=self.vecm_obj)

    def test_var_unique_constraint(self):
        try:
            var_obj = VAR.objects.create(p=self.p)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e) and \
                "Key (p)=" in str(e):
                pass
            else:
                raise

    def test_varma_unique_constraint(self):
        try:
            varma_obj = VARMA.objects.create(p=self.p)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e) and \
                "DETAIL:  Key (varma_id)=" in str(e):
                pass
            else:
                raise

    def test_vecm_unique_constraint(self):
        try:
            vecm_obj = VECM.objects.create(p=self.p)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e) and \
                "DETAIL:  Key (vecm_id)=" in str(e):
                pass
            else:
                raise

    def test_store_technique_model_including_unique_constraint(self):
        try:
            tech_var2 = TECH.objects.create(var=self.var_obj)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e) and \
                "DETAIL:  Key (var_id)=":
                pass
            else:
                raise
        try:
            tech_varma2 = TECH.objects.create(varma=self.varma_obj)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e) and \
                "DETAIL:  Key (varma_id)=":
                pass
            else:
                raise
        try:
            tech_vecm2 = TECH.objects.create(vecm=self.vecm_obj)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e) and \
                "DETAIL:  Key (vecm_id)=":
                pass
            else:
                raise
        try:
            tech_wrong = TECH.objects.create(var=self.var_obj, varma=self.varma_obj)
        except IntegrityError as e:
            if str(e) == """Two fields must be null. Either only VAR, or only VARMA,
                or only VECM object must be provided, but not more than one of each object.""":
                pass
            else:
                raise
        try:
            tech_wrong = TECH.objects.create(var=self.var_obj, vecm=self.vecm_obj)
        except IntegrityError as e:
            if str(e) == """Two fields must be null. Either only VAR, or only VARMA,
                or only VECM object must be provided, but not more than one of each object.""":
                pass
            else:
                raise
        try:
            tech_wrong = TECH.objects.create(varma=self.varma_obj, vecm=self.vecm_obj)
        except IntegrityError as e:
            if str(e) == """Two fields must be null. Either only VAR, or only VARMA,
                or only VECM object must be provided, but not more than one of each object.""":
                pass
            else:
                raise
        try:
            tech_wrong = TECH.objects.create(var=self.var_obj, varma=self.varma_obj, vecm=self.vecm_obj)
        except IntegrityError as e:
            if str(e) == """Two fields must be null. Either only VAR, or only VARMA,
                or only VECM object must be provided, but not more than one of each object.""":
                pass
            else:
                raise
        try:
            tech_wrong = TECH.objects.create()
        except IntegrityError as e:
            if str(e) == """All fields cannot be null. You must input
                either a VAR, VARMA, or VECM object.""":
                pass
            else:
                raise

    def test_get_technique_method_of_technique_model(self):
        tech_obj = self.tech_var.technique()
        self.assertEqual(type(tech_obj), VAR)

        tech_obj = self.tech_varma.technique()
        self.assertEqual(type(tech_obj), VARMA)

        tech_obj = self.tech_vecm.technique()
        self.assertEqual(type(tech_obj), VECM)

    def test_adjust_variables(self):

        pyyc = PYYC()

        q, seasons, deterministic = pyyc.adjust_variables(self.tech_var)

        self.assertEqual(q, 0)
        self.assertEqual(seasons, None)
        self.assertEqual(deterministic, None)

        q, seasons, deterministic = pyyc.adjust_variables(self.tech_varma)

        self.assertEqual(q, self.tech_varma.varma.q)
        self.assertEqual(seasons, None)
        self.assertEqual(deterministic, None)

        q, seasons, deterministic = pyyc.adjust_variables(self.tech_vecm)

        self.assertEqual(q, 0)
        self.assertEqual(seasons, self.tech_vecm.vecm.seasons)
        self.assertEqual(deterministic, self.tech_vecm.vecm.deterministic)

class UpdateDataTests(TestCase):
    # fixtures = ["yields.json"]

    @classmethod
    def setUpTestData(self):

        historical_bulkcreate()
        update_bocgic(one_time=True)
        create_techniques()

    def test_get_new_data(self):
        update_data()
        df = make_combined_frame()

        self.assertFalse(df.isnull().values.any())

    def test_technique_manager_methods(self):
        ps = [1, 12, 24, 36, 48, 60]
        self.assertEqual(TECH.objects.ps(), ps)
        qs = [1, 2, 3]
        self.assertEqual(TECH.objects.qs(), qs)
        seasons = [12, 24, 36, 48]
        self.assertEqual(TECH.objects.seasons(), seasons)

class BOCGICTests(TestCase):
    # fixtures = ["yields.json"]

    @classmethod
    def setUpTestData(self):
        historical_bulkcreate()
        create_techniques()

        pyyc = PYYC()
        raw = pyyc.save_raw(inf_bool=False, gap_bool=False, n_diffs=0, df=pyyc.df)
        pca, pc = pyyc.save_pca(raw, n_comp=3, use_pca=True)
        dataset = pyyc.save_dataset(pc=pc)

        technique = TECH.objects.get(vecm_id=1)
        pyyc.save_coint(dataset, "5%", technique.vecm.deterministic, technique.vecm.p)

        self.forecast = pyyc.save_forecast(dataset, technique, pca=pca)

        self.df_proj = self.forecast.df()

        gic1 = "BOC/V122524"
        gic3 = "BOC/V122525"
        gic5 = "BOC/V122526"
        prime = "BOC/V122495"

        rates = [gic1, gic3, gic5, prime]
        dfs = [quandl.get(rate) for rate in rates]
        self.df = pd.concat(dfs, axis=1)
        self.df = self.df / 100
        self.df.reset_index(inplace=True)
        self.df.columns = [f.name for f in BOCGICs._meta.get_fields() if f.name not in ["id", "date_added", "date_modified"]]

    def test_upload_bocgics(self):
        update_bocgic(one_time=True)

        # Test that dataframes are equal
        df_query = pd.DataFrame(list(BOCGICs.objects.all().values())).drop(["id", "date_added", "date_modified"], axis=1)
        df_query = df_query[["date", "one_year", "three_year", "five_year", "prime"]]
        df_query["date"] = pd.to_datetime(df_query["date"])

        assert_frame_equal(self.df, df_query, check_dtype=False)

    def test_update_bocgics(self):
        gic1 = "BOC/V122524"
        gic3 = "BOC/V122525"
        gic5 = "BOC/V122526"
        prime = "BOC/V122495"

        rates = [gic1, gic3, gic5, prime]
        dfs = [quandl.get(rate) for rate in rates]
        df = pd.concat(dfs, axis=1)
        df = df / 100
        df = df.iloc[:-1]
        df.reset_index(inplace=True)
        df.columns = [f.name for f in BOCGICs._meta.get_fields() if f.name not in ["id", "date_added", "date_modified"]]
        BOCGICs.objects.bulk_create(BOCGICs(**vals) for vals in df.to_dict("records"))

        update_bocgic()

        # Test that dataframes are equal
        df_query = pd.DataFrame(list(BOCGICs.objects.all().values())).drop(["id", "date_added", "date_modified"], axis=1)
        df_query = df_query[["date", "one_year", "three_year", "five_year", "prime"]]
        df_query["date"] = pd.to_datetime(df_query["date"])

        assert_frame_equal(self.df, df_query, check_dtype=False)

    def test_gic_regression(self):
        update_bocgic(one_time=True)
        pyyc = PYYC()
        gics = pyyc.save_gic_forecast(self.forecast)

        # print (gics.df().head())
        # print (gics.split_rates())

class DatasetTests(TestCase):
    # fixtures = ["yields.json"]

    @classmethod
    def setUpTestData(self):

        historical_bulkcreate()
        update_bocgic(one_time=True)
        update_data()

        self.pyyc = PYYC()
        self.raw = self.pyyc.save_raw(inf_bool=False, gap_bool=False, n_diffs=0, df=self.pyyc.df)
        self.raw2 = self.pyyc.save_raw(inf_bool=True, gap_bool=True, n_diffs=0, df=self.pyyc.df)

    def test_save_raw_and_dataset(self):

        dataset = self.pyyc.save_dataset(raw=self.raw)
        n_diffs = dataset.n_diffs()
        data = dataset.df()

        self.assertEqual(n_diffs, 0)
        self.assertEqual(data.index.names, ["date"])
        try:
            dataset.nodiff_df().tail()
        except AttributeError as e:
            if str(e) == "'NoneType' object has no attribute 'tail'":
                pass
            else:
                raise

    def test_make_yields_df(self):
        # make_yields_df() should return same output for same data, regardless of inf_bool or gap_bool
        assert_frame_equal(self.raw.yields_df(), self.raw2.yields_df(), check_dtype=False)

        # test access make_yields_df() via dataset
        dataset = self.pyyc.save_dataset(raw=self.raw2)
        assert_frame_equal(dataset.raw.yields_df(), self.raw2.yields_df(), check_dtype=False)

    def test_make_external_df(self):
        self.assertTrue(self.raw.external_df().empty)
        assert_frame_equal(self.raw2.external_df(), make_combined_frame()[["inflation", "output_gap"]])

        dataset = self.pyyc.save_dataset(raw=self.raw2)
        dataset_again = pd.concat([self.raw2.yields_df(), self.raw2.external_df()], axis=1)
        assert_frame_equal(dataset.df()[dataset_again.columns], dataset_again)

    def test_save_pc_and_dataset(self):
        pca, pc = self.pyyc.save_pca(self.raw, use_pca=False)
        self.assertEqual(pca, pc, None)
        try:
            dataset = self.pyyc.save_dataset(raw=self.raw, pc=pc)
        except IntegrityError as e:
            if "DETAIL:  Key (pc_id)=(1) already exists." in str(e):
                pass
            else:
                raise

        pca, pc = self.pyyc.save_pca(self.raw)
        self.assertTrue(pca, pc)

        # Testing Dataset Model custom methods
        dataset = self.pyyc.save_dataset(pc=pc)
        self.assertEqual(dataset.n_diffs(), 0)
        data = dataset.df()
        self.assertEqual(data.index.names, ["date"])
        self.assertFalse("inflation" in data.columns)
        self.assertFalse("output_gap" in data.columns)
        try:
            dataset.nodiff_df().tail()
        except AttributeError as e:
            if str(e) == "'NoneType' object has no attribute 'tail'":
                pass
            else:
                raise
        # Test errors raised on invalid raw/pc input
        try:
            dataset3 = self.pyyc.save_dataset(raw=self.raw, pc=pc)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e) and \
                "DETAIL:  Key (pc_id)=" in str(e):
                pass
            else:
                raise
        try:
            dataset4 = self.pyyc.save_dataset()
        except TypeError as e:
            if str(e) == "one of raw or pc must be provided. the other must be None":
                pass
            else:
                raise
        # Test errors raised on violating unique constraints
        try:
            dataset5 = self.pyyc.save_dataset(pc=pc)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e) and \
                "DETAIL:  Key (pc_id)=":
                pass
            else:
                raise
        try:
            dataset6 = self.pyyc.save_dataset(raw=self.raw)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e) and \
                "DETAIL:  Key (raw_id)=" in str(e):
                pass
            else:
                raise

        pca, pc = self.pyyc.save_pca(self.raw2)
        self.assertTrue(pca, pc)

        # Testing Dataset Model custom methods
        dataset = self.pyyc.save_dataset(pc=pc)
        self.assertEqual(dataset.n_diffs(), 0)

        data = dataset.df()
        self.assertTrue("PC 1" in data.columns)
        self.assertTrue("PC 2" in data.columns)
        self.assertTrue("PC 3" in data.columns)
        self.assertTrue("inflation" in data.columns)
        self.assertTrue("output_gap" in data.columns)

    def test_save_pc_and_raw_with_n_diffs(self):
        raw_diff = self.pyyc.save_raw(inf_bool=False, gap_bool=False, n_diffs=1, df=self.pyyc.df)

        pca, pc = self.pyyc.save_pca(raw_diff, use_pca=False)
        self.assertEqual(pca, pc, None)

        # Testing Dataset Model custom methods
        dataset = self.pyyc.save_dataset(raw=raw_diff)
        self.assertEqual(1, dataset.n_diffs())

        data = dataset.df()
        self.assertEqual(data.index.names, ["date"])
        self.assertFalse("PC 1" in data.columns)
        self.assertFalse("PC 2" in data.columns)
        self.assertFalse("PC 3" in data.columns)
        self.assertFalse("inflation" in data.columns)
        self.assertFalse("output_gap" in data.columns)

        pca, pc = self.pyyc.save_pca(raw_diff)
        self.assertTrue(pca, pc)

        # Testing Dataset Model custom methods
        dataset2 = self.pyyc.save_dataset(pc=pc)
        self.assertEqual(1, dataset2.n_diffs())

        assert_frame_equal(dataset2.nodiff_df(), self.pyyc.df.drop(columns=["inflation", "output_gap"], axis=1)[dataset2.nodiff_df().columns])

        # Test errors raised on invalid raw/pc input
        try:
            dataset3 = self.pyyc.save_dataset(raw=raw_diff, pc=pc)
        except IntegrityError as e:
            if "duplicate key value violates unique constraint" in str(e) and \
                "DETAIL:  Key (pc_id)=" in str(e):
                pass
            else:
                raise
        try:
            dataset4 = self.pyyc.save_dataset()
        except TypeError as e:
            if str(e) == "one of raw or pc must be provided. the other must be None":
                pass
            else:
                raise

        raw_diff2 = self.pyyc.save_raw(inf_bool=True, gap_bool=True, n_diffs=1, df=self.pyyc.df)
        pca, pc = self.pyyc.save_pca(raw_diff2)
        self.assertTrue(pca, pc)

        # Testing Dataset Model custom methods
        dataset = self.pyyc.save_dataset(pc=pc)
        self.assertEqual(dataset.n_diffs(), 1)

        data = dataset.df()
        self.assertTrue("PC 1" in data.columns)
        self.assertTrue("PC 2" in data.columns)
        self.assertTrue("PC 3" in data.columns)
        self.assertTrue("inflation" in data.columns)
        self.assertTrue("output_gap" in data.columns)

    def test_run_coints_and_save(self):
        dataset = self.pyyc.save_dataset(raw=self.raw)
        root_crit = "5%"
        det = "c"
        p = 120
        self.pyyc.save_coint(dataset, root_crit, det, p)

        self.pyyc.save_multiple_coints(dataset)

        # test unique constraint in Cointegration
        try:
            self.pyyc.save_coint(dataset, root_crit, det, p)
        except IntegrityError as e:
            if "DETAIL:  Key (dataset_id, p, deterministic, root_crit)" in str(e):
                pass
            else:
                raise

class FullPYYCTests(TestCase):
    fixtures = ["yields.json"]

    @classmethod
    def setUpTestData(self):
        historical_bulkcreate()
        # create_techniques()
        update_bocgic(one_time=True)
        update_data()

    @tag("full")
    def test_full_process_for_all_data(self):
        start = time.time()
        ps = [1, 12, 24, 36, 48, 60]
        qs = [1, 2, 3]
        seasons = [12, 24, 36, 48]
        pyyc_obj = PYYC(ps=ps, qs=qs, seasons=seasons)
        pyyc_obj.pyyc()

        forecasts = Forecast.objects.order_by("total_rmse")[:10]
        for forecast in forecasts:
            print (forecast.group, forecast.dataset, forecast.technique, forecast.total_rmse)

        end = time.time()
        process_time = end - start

        print ("Seconds to process all raw datasets: {}".format(process_time))
