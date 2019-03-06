from datetime import datetime as dt, timedelta, date
from dateutil.relativedelta import relativedelta
from collections import Counter
import pandas as pd
import numpy as np

from django.utils import timezone
from django.db.models import QuerySet, Sum
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from reservefundstudy.models import Study, Contributions, Expenditures
from condo.models import Condo, BankAccounts, AccountBalance, Investments
from investmentplan.helpers import find_dates, find_period
from pyyc.models import Forecast

class Converter():
    """
    Takes Django querysets and converts them for use in Pyondo
    """

    def __init__(self, condo_id, study_id, spread=None, naive_rates=False, rates=None):
        """
        > account balance and existing investment info is compiled
        > future interest and maturity amounts from existing investments
          are determined using _get_existing_interest and _get_existing_maturities
        > the number of periods is reduced to match the date of the account balance entry
        > dates array is trimmed to match number of periods
        """
        if not isinstance(rates, tuple) and rates is not None:
            raise TypeError("Rates must be a tuple or None")
        if condo_id is None or study_id is None:
            raise ValueError("You must provide condo_id and study_id")

        if rates is not None and isinstance(rates, tuple):
            self.given_rates = rates
        else:
            self.given_rates = None

        self.condo = Condo.objects.get(pk=condo_id)
        self.study = Study.objects.get(pk=study_id)

        self.years = self.study.years
        self.first_year = self.study.first_year
        self.last_year = self.study.last_year
        self.opening_balance = self.study.opening_balance
        self.contributions = Contributions.objects.filter(study=self.study)
        self.expenditures = Expenditures.objects.filter(study=self.study)

        self.periods = self.years * 12
        self.dates = find_dates(self.first_year, self.periods)
        self.naive_rates = naive_rates

        """
        First, check that bank account and account balance info is properly configured
        Then, make changes to attributes
        """
        self.bank_account = BankAccounts.objects.filter(condo=self.condo).get(type="RESERVE")
        if not self.bank_account:
            raise ObjectDoesNotExist("You need to input Reserve bank account information for this Condo")

        self.account_balance = AccountBalance.objects.filter(account=self.bank_account).latest("date_added")
        if not self.account_balance:
            raise ObjectDoesNotExist("You need to input the latest account balance information for account {}".format(self.account_balance))
        else:
            self.bank_balance = self.account_balance.balance

        self.first_period = find_period(self.first_year, self.account_balance.date)

        self.periods -= self.first_period
        self.dates = self.dates[self.first_period:]
        self.spread = self.bank_account.spread

        if len(self.dates) != self.periods:
            raise ValueError("The length of the dates array does not match the new period")

        self.investments = Investments.objects.current(condo=self.condo)
        if self.investments:
            self.opening_invmts = self.investments.aggregate(Sum("amount"))["amount__sum"]
        else:
            self.opening_invmts = 0

    def _set_rates(self):
        """
        Sets the interest rates used
        > Pulls from PYYC; uses current BOCGICForecast
        > substracts spread from bank_rates
        > makes any negative rate equal to 0

        Returns: tuple of projected bank account rates and rates for each investment type
        """
        if self.naive_rates:
            rates = [[0.01, 0.02, 0.03, 0.04, 0.05] for x in range(self.periods)]
            bank_rates = [0.008 for x in range(self.periods)]
        else:
            current = Forecast.objects.get(current=True)
            bank_rates, rates = current.bocgicforecast.split_rates(length=len(self.dates))
            bank_rates = [rate - self.spread for rate in bank_rates]
            bank_rates = self._make_zero(bank_rates)
            rates = [self._make_zero(period) for period in rates]

        return bank_rates, rates

    def _make_zero(self, rates):
        """Makes any negative rate equal to 0"""
        return [i if i >=0 else 0 for i in rates]

    def _get_annual_flows(self, flows):
        """
        Parameters
        ----------
        Flows: queryset or dictionary; contributions or expenditures for the study

        If flows is queryset, convert to list of tuples for just
        the cash flow attributes and only for number of years in the study
        Null attribute values should be eliminated from result

        """
        if isinstance(flows, QuerySet):
            flows = [value for key, value in flows.values()[0].items() if key[0:4] == "cont" or key[0:3] == "exp"]
        else:
            raise TypeError("flows parameter must be type dict or QuerySet")
        return flows[:self.years]

    def _get_monthly_flows(self, flows):
        """
        Convert annual contributions or expenditures to monthly values using
        Pandas Series object
        Creates DateTimeIndex from Study model values then reindexes across
        monthly . Adds extra month on backend, which must be removed.
        Returns a list
        """
        rng = pd.date_range("{}".format(self.first_year), periods=self.years, freq="AS")
        ts = pd.Series(self._get_annual_flows(flows), index=rng)
        monthly = (ts.reindex(pd.DatetimeIndex(start=ts.index[0], end=ts.index[-1] + 1, freq="MS"), method="pad") / 12)[:-1]
        return monthly.tolist()[self.first_period:]

    def _get_existing_interest(self):
        """
        Loops through existing investments
        Converts the maturity date to the first day of the month,
        Finds the period corresponding to the maturity,
        Creates a list of the periods in which interest payments occur (the list is
        sorted in reverse order and adjusted based on the number of payment periods per year)
        Then creates a list of dictionaries with each payment period and the interest payment
        Finally, returns the sum of the interest payments in each dictionary using Counter()
        If their are no investments, dct = Counter() and returns None
        """
        existing_interest = []

        if self.investments:
            for invmt in self.investments:
                maturity_date = timezone.make_aware(dt(invmt.maturity_date.year, invmt.maturity_date.month, 1) + relativedelta(months=1,days=-1))
                maturity_period = self.dates.index(maturity_date) + 1
                # For payment_periods below:
                # [::-1] inverts the list below; [::invmt._find_freq()] elminates all accept the nth payment according interest frequency
                payment_periods = [i for i in range(1, maturity_period + 1)][::-1][::invmt._find_frequency()]
                interest_payment = invmt.amount * invmt.interest_rate * (invmt._find_frequency() / 12)
                payments = {period: interest_payment for period in payment_periods }
                existing_interest.append(payments)

        dct = sum( (Counter(dict(x)) for x in existing_interest), Counter() )
        return dct if dct != Counter() else {}

    def _get_existing_maturities(self):
        existing_maturities = []

        for invmt in self.investments:
            maturity_date = timezone.make_aware(dt(invmt.maturity_date.year, invmt.maturity_date.month, 1) + relativedelta(months=1,days=-1))
            maturity_period = self.dates.index(maturity_date) + 1
            maturity = {maturity_period: invmt.amount}
            existing_maturities.append(maturity)

        dct = sum( (Counter(dict(x)) for x in existing_maturities), Counter() )
        return dct if dct != Counter() else {}

    def make_kwargs(self):
        kwargs = {}
        kwargs["periods"] = self.periods
        kwargs["bank_rates"], kwargs["rates"] = self._set_rates() if not self.given_rates else self.given_rates

        kwargs["contributions"] = self._get_monthly_flows(self.contributions)
        kwargs["expenditures"] = self._get_monthly_flows(self.expenditures)

        kwargs["opening_reserve"] = self.bank_balance + self.opening_invmts
        kwargs["opening_balance"] = self.bank_balance

        kwargs["existing_interest"] = self._get_existing_interest()
        kwargs["existing_maturities"] = self._get_existing_maturities()

        return kwargs
