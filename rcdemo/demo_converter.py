from investmentplan.converter import Converter
from investmentplan.helpers import find_dates

class DemoConverter(Converter):
    """
    1) demo=True
        > no account or investment info is required
        > converter prepares the periods and net flows based on entire the
          period of Reserve Fund Study
        > parameters must be passed directly
    """

    def __init__(self, opening_balance=None, contributions=None, expenditures=None,
                first_year=None, last_year=None, years=None, spread=None,
                naive_rates=False, rates=None):

        if (contributions is None or expenditures is None or
            first_year is None or last_year is None or years is None):
            raise ValueError("first_year, last_year, years, contributions, expenditures are required parameters in Demo Mode")

        if not isinstance(contributions, dict) or not isinstance(expenditures, dict):
            raise TypeError("contributions and expenditures must be of type dict")

        self.first_year = first_year
        self.last_year = last_year
        self.years = years
        self.opening_balance = opening_balance
        self.contributions = contributions
        self.expenditures = expenditures
        self.first_period = 0
        self.bank_balance = 0
        self.opening_invmts = 0

        self.periods = self.years * 12
        self.dates = find_dates(self.first_year, self.periods)
        self.naive_rates = naive_rates

        if spread:
            self.spread = spread
        else:
            self.spread = 0.03

        self.bank_rates, self.rates = self._set_rates() if not rates else rates

    def _get_existing_interest(self):
        return {}

    def _get_existing_maturities(self):
        return {}

    def _get_annual_flows(self, flows):
        """
        Parameters
        ----------
        Flows: dictionary; contributions or expenditures for the study

        Null attribute values should be eliminated from result

        """

        if isinstance(flows, dict):
            flows = [value for key, value in flows.items()]
        else:
            raise TypeError("flows parameter must be type dict or QuerySet")
        return flows[:self.years]

    def make_kwargs(self):
        kwargs = super().make_kwargs()
        kwargs["opening_reserve"]= kwargs["opening_balance"] = self.opening_balance

        return kwargs
