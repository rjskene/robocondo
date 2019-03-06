import time
import socket
from datetime import datetime as dt, date
from dateutil.relativedelta import relativedelta
import pandas as pd

from django.db import transaction

from pyyc.models import HistoricalYieldCurve as HYC, HistoricalOvernightRate as HOR, \
                        InflationRate as INFR, OutputGap as GAP, RAW, \
                        PrincipalComponents as PC, Dataset, Cointegration as COINT, Technique as TECH, \
                        VAR, VARMA, VECM, Forecast, BOCGICs, BOCGICForecast
from pyyc.data.combine import make_combined_frame, make_frame
from .analysis import PCA, CointAnal
from .forecast import YieldCurveForecast, GICForecast

class PYYC:
    """
    Main Class
    >>>Create and store yield curve forecasts
    >>>Forecasts are created from data stored in HYC, HOR, INFR, & GAP models
    >>>These models are combined into a single pandas dataframe

    Main method pyyc is designed to process forecasts across every technique in
    TECH model, however, helper methods can all be used for handling and analysis
    of individual datasets with individual techniques

    POTENTIAL UPDATES:
    >>> Perhaps multiple inheritance will be useful; could be way to separate more
        clearly from Django database
    >>> root_crit, p-,q-,seasons, dets are attributes of a "TECHNIQUE" class?
    >>> n_comp is attribute of PCA class? how many PCA classes can i handle???
    """

    def __init__(self, df=None, n_diffs=None, n_comp=3, root_crit="5%", steps=360,
                ps=None, qs=None, seasons=None, dets=None, **kwargs):

        self.df = make_combined_frame() if not df else df
        self.last_date = self.df.tail(1).index[0].to_pydatetime()

        self.inf_bools = [True, False]
        self.gap_bools = [True, False]
        self.n_diffs = [0,1] if not n_diffs else n_diffs

        self.use_pcas = [False, True]
        self.n_comp = n_comp
        self.root_crit = root_crit

        self.ps = TECH.objects.ps() if not ps else ps
        self.qs = TECH.objects.qs() if not qs else qs
        self.seasons = TECH.objects.seasons() if not seasons else seasons
        self.dets = [choice[1] for choice in COINT.DET.choices()] if not dets else dets

        self.steps = steps

        try:
            Forecast.objects.latest("group")
            self.forecast_group = Forecast.objects.latest("group").group + 1

        except Forecast.DoesNotExist:
            self.forecast_group = 1

    @transaction.atomic
    def pyyc(self, skip_varma=True):
        """
        Main method of PYYC; generates forecasts for all raw datasets (including
        principal components of each raw dataset) for each regression technique

        1) Create and store set of raw datasets from the dataframe provided
        2) loop through each raw dataset
        3) for each data set, either use raw data or princal components
        4) if use_pca==True, save_pca returns values, if use_pca==False save_pca returns None tuple
        5) if pc==None, save_dataset point to raw model; if pc==not None, save_dataset
            points to PrincipalComponents model
        6) complete cointegration analysis and store for all datasets
        7) save_forecast for each dataset; pca object passed to allow inverse_transform
           of pc dataset back to raw

        save_pca will return pc==None if use_pca==False; then save_dataset
        will save the raw object

        Parameters
        -------
        skip_varma: if False, varma analysis will be performed

        Returns
        -------
        nada
        """
        raws = self.save_multiple_raws()

        for raw in raws:
            for use_pca in self.use_pcas:
                pca, pc = self.save_pca(raw, 3, use_pca)
                dataset = self.save_dataset(raw=raw, pc=pc)
                self.save_multiple_coints(dataset)

                print ("Attempting to generate forecast...")
                self.save_forecast_for_all_techniques(dataset, pca, skip_varma=skip_varma)
        print ("PYYC complete")

    def save_raw(self, inf_bool, gap_bool, n_diffs, df):
        raw = RAW(inflation=inf_bool, output_gap=gap_bool, n_diffs=n_diffs)
        raw.save(df=df)

        return raw

    def save_multiple_raws(self):
        raws = []
        for inf_bool in self.inf_bools:
            for gap_bool in self.gap_bools:
                for n in self.n_diffs:
                    raws.append(self.save_raw(inf_bool, gap_bool, n, self.df))
        return raws

    def save_pca(self, raw, n_comp=3, use_pca=True):
        """
        Principal Component analysis should only be performed on Yield Curve components
        Other data should be excluded then reattached to data df
        """
        if use_pca == True:
            data = raw.yields_df()

            pca = PCA(data=data, n_components=n_comp)
            pc = PC(raw=raw, n=n_comp, explained=pca.explained)
            pc.save(df=pca.df)
        elif use_pca == False:
            pca = None
            pc = None
        else:
            raise ValueError("use_pca must be boolean")

        return pca, pc

    def save_dataset(self, raw=None, pc=None):
        if raw and not pc:
            return Dataset.objects.create(raw=raw)
        elif not raw and not pc:
            raise TypeError("one of raw or pc must be provided. the other must be None")
        elif pc:
            return Dataset.objects.create(pc=pc)

    def save_coint(self, dataset, root_crit, det, p):
        data = dataset.df()
        coint_anal = CointAnal(data=data, crit=root_crit, reg=det, k_ar_diff=p)

        coint_obj = COINT.objects.create(dataset=dataset,
            p=p, deterministic=det, any_roots=coint_anal.any_unitroots,
            root_crit=root_crit, diffs_to_stationary=coint_anal.n_diffs,
            rank=coint_anal.jres.coint_rank, signif=coint_anal.jres.signf_level
        )

    def save_multiple_coints(self, dataset):
        for p in self.ps:
            for det in self.dets:
                self.save_coint(dataset, self.root_crit, det, p)

    def adjust_variables(self, technique):
        """
        Adjusts q value to 0 if VARMA is not used
        Adjusts seasons, deterministic values to None if a VECM model is not used

        Parameters
        -------
        technique: foreignkey object of VAR, VARMA, or VECM model.
                    attributes of the object will populate Forecast Variables

        Returns
        -------
        q: q-value for VARMA
        seasons: season length used in VECM regression
        deterministic: deterministic structure used in VECM regression
        """
        tech_obj = technique.technique()
        assert type(tech_obj) == VAR or type(tech_obj) == VARMA or type(tech_obj) == VECM

        if type(tech_obj) != VECM:
            seasons = None
            deterministic = None
        else:
            seasons = tech_obj.seasons
            deterministic = tech_obj.deterministic

        q = 0 if type(tech_obj) != VARMA else tech_obj.q

        return q, seasons, deterministic

    def save_forecast(self, dataset, technique, pca):
        coints = COINT.objects.filter(dataset=dataset)
        execute = False

        print ("Dataset {}".format(dataset))
        print ("Technique {}".format(technique))

        if technique.var:
            roots = [record.any_roots for record in coints.filter(p=technique.var.p)]
            if any(roots):
                print ("VAR not applied because the dataset has roots")
                pass
            else:
                execute = True
                p = technique.var.p
                q, seasons, deterministic = self.adjust_variables(technique)
        if technique.varma:
            roots = [record.any_roots for record in coints.filter(p=technique.varma.p)]
            if any(roots):
                print ("VARMA not applied because the dataset has roots")
                pass
            else:
                execute = True
                p = technique.varma.p
                q, seasons, deterministic = self.adjust_variables(technique)
        if technique.vecm and dataset.pc:
            # SKIP VECM IF RAW DATASET IS USED! Not accurate at all
            vecm_coint = coints.get(p=technique.vecm.p,
                        deterministic=technique.vecm.deterministic
            )
            if vecm_coint.any_roots and vecm_coint.rank > 1:
                execute = True
                p = technique.vecm.p
                q, seasons, deterministic = self.adjust_variables(technique)
            else:
                if not vecm_coint.rank or vecm_coint.rank <= 1:
                    print ("VECM not applied because cointegration rank is 1 or None")
                    print ("p", technique.vecm.p, "det", technique.vecm.deterministic)
                pass
        elif dataset.raw:
            print ("VECM not applied to RAW datasets")

        if execute:
            if dataset.pc:
                data = pca
                external_data = dataset.pc.raw.external_df()
            else:
                data = dataset.df()
                external_data = None

            n_diffs = dataset.n_diffs()
            nodiff_data = dataset.nodiff_df()
            use_model = technique.use_technique()

            yc = YieldCurveForecast(data=data, external_data=external_data,
                                    n_diffs=n_diffs, nodiff_data=nodiff_data
            )

            try:
                ycf, _, _1 = yc.forecast(use_model=use_model, steps=self.steps,
                                    order=(p, q), seasons=seasons,
                                    deterministic=deterministic, freq="M"
                )
                tot_rmse, set_rmses, df_trains  = yc.train(use_model=use_model,
                                                                 test_len=60,
                                                                 order=(p, q),
                                                                 seasons=seasons,
                                                                 deterministic=deterministic,
                                                                 freq="M"
                )
                forecast = Forecast.objects.create(group=self.forecast_group, dataset=dataset,
                                technique=technique,
                                process_time=yc.process_time, set_rmses=set_rmses,
                                total_rmse=tot_rmse, projected=ycf.to_json(orient="index")
                )
                print ("Forecast generated for dataset {} using Technique {}".format(dataset, technique))
                print ("GROUP #", forecast.group)
                return forecast
            except Exception as e:
                # This error comes up on very few vecm models; I do not understand it
                # Catch it and skip it
                if """Cannot cast ufunc add output from dtype('complex128') to dtype('float64') with casting rule 'same_kind'""" == str(e):
                    print ("This error occured: {}".format(str(e)))
                else:
                    raise
        else:
            print ("""no forecast created""")

    def gic_forecast_frames(self, forecast):
        """
        Make the dataframes to create GICForecast object
        """

        df_bocgic = make_frame(BOCGICs)
        df_bocgic.rename(columns={"prime": "rate"}, inplace=True)

        # estimate two & four year gic as average of surrounding rates
        df_bocgic["two_year"] = df_bocgic[["one_year", "three_year"]].mean(axis=1)
        df_bocgic["four_year"] = df_bocgic[["three_year", "five_year"]].mean(axis=1)
        df_bocgic = df_bocgic[["rate", "one_year", "two_year", "three_year", "four_year", "five_year"]]

        first_date = BOCGICs.objects.earliest("date").date

        excluded = ["id", "date_added", "date_modified", "three_month",
                "six_month", "seven_year", "ten_year", "twenty_five_year"
        ]
        df_hyc = make_frame(HYC, excluded=excluded, filter=True, date__gte=first_date)
        df_hor = make_frame(HOR, filter=True, date__gte=first_date)
        df = pd.concat([df_hor, df_hyc.resample("M").mean()], axis=1)

        df_proj = forecast.df()

        return df, df_bocgic, df_proj

    def save_gic_forecast(self, forecast):
        args = self.gic_forecast_frames(forecast)
        gics_forecast = GICForecast(*args)
        try:
            df_proj_gic = gics_forecast.forecast()

            gic_obj = BOCGICForecast(forecast=forecast)
            gic_obj.save(df=df_proj_gic)
            print ("GIC Forecast completed")
            return gic_obj
        except Exception as e:
            if "Input contains NaN, infinity or a value too large for dtype('float64')" in str(e):
                print ("GIC Forecast Error: {}".format(str(e)))
            else:
                raise

    def save_forecast_for_all_techniques(self, dataset, pca, skip_varma=True):
        for technique in TECH.objects.all():
            if technique.varma and skip_varma:
                    pass
            else:
                forecast = self.save_forecast(dataset, technique, pca)
                if forecast:
                    self.save_gic_forecast(forecast)
                    print ("GIC Forecast Generated for {}".format(forecast))
