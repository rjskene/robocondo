import pandas as pd
import numpy as np
from operator import sub
from itertools import chain
from collections import OrderedDict
from pyomo.environ import *
from pyomo.opt import SolverFactory

class Pyondo:
    """
    Class to generate investment plan from reservefundstudy projection and interest
    rate projection
    """
    MINIMUM_BANK_BALANCE = 100000
    MinIA = 25000 # currently unutilized
    MaxIA = 10000000    # currently unutilized
    TERMS = 5
    # TERMS = [12, 24, 36, 48, 60]
    BLP = 0.005 / 12    # liquidity premium for bank balances; currently unutilized

    REQUIRED_KEYS = [
                    "periods", "contributions", "expenditures", "opening_balance",
                     "opening_reserve", "rates", "bank_rates"
    ]
    OPTIONAL_KEYS = ["existing_interest", "existing_maturities"]
    REQUIRED_TYPES = {
            "existing_interest": dict, "existing_maturities": dict,
            "periods": int, "contributions": list, "expenditures": list,
            "bank_rates": list, "rates": list,
            "opening_balance": float, "opening_reserve": float
    }
    REQUIRED_LISTS = [key for key, value in REQUIRED_TYPES.items() if value == list]

    def __init__(self, **kwargs):
        """
        > OPTIONAL_KEYS: if not provided, these are set to None
        > REQUIRED_LISTS is used to compare the length of all list type items
        to ensure they are equal length as part of _same_length() method
        """
        if not self._same_length(**kwargs):
            raise ValueError(
                """
                Your inputs of type list/numpy array are not equal length.
                Check pyondo.REQUIRED_LISTS
                """
            )
        for key, value in kwargs.items():
            if (key not in self.REQUIRED_KEYS and key not in self.OPTIONAL_KEYS):
                raise IndexError(
                    """
                    Kwargs included an incorrect key. See REQUIRED_KEYS and OPTIONAL_KEYS
                    for list of required keys.
                    """, key
                )
            else:
                if not isinstance(value, self.REQUIRED_TYPES[key]):
                    raise TypeError(
                        """
                        Kwargs contained object of the wrong type; 'existing_interest' and 'existing_maturities' require dict, \
                        'opening_balance' and 'opening_reserve' require float, \
                        remainder require list
                        """, key
                    )
                else:
                    self.__setattr__(key, value)

        # Sets existing_interest and existing_maturities to None if not delivered
        for key in self.OPTIONAL_KEYS:
            if key not in kwargs.keys():
                self.__setattr__(key, None)

        self._net_flows = self._find_net_cash_flow()

    def _same_length(self, **kwargs):
        """
        Tests if objects of type list are the same length
        Returns True or False
        """
        lists = [(key, value[-24:]) for key, value in kwargs.items() if key in self.REQUIRED_LISTS]
        list_lengths = [len(value) for key, value in kwargs.items() if key in self.REQUIRED_LISTS]
        return len(set(list_lengths)) == 1

    def _find_net_cash_flow(self):
        """
        Find net cash flow for a monthly period.
        Subtracts list of monthly contributions from list of monthly expenditures
        Returns list
        """
        return list(map(sub, self.contributions, self.expenditures))

    def _build_int_constraint(self, period, term, investments):
        """
        Builds the Interest constraint for each investment term in each period.
        > Loops over term and adds to the constraint at each new investment term
        > Each new interest payment is received from the investment made [period - (12 * n)] periods
        ago multiplied by the interest rate in the same period
        > If the period is less than term of the investment, than
        ***THIS ASSUMES ONLY ANNUAL INTEREST PAYMENTS***

        PARAMETERS:
        > period: the current period for which the constraint is being built
        > term: the current investment term for which the constraint is being built
        > investments: model.Investments array of dimensions [periods, terms]

        RETURNS:
        > interest constraint specific to [period, term]
        """
        constraint = 0

        for n in range(1, term + 1):
            constraint += investments[period - (12 * n), term] * self.rates[period - (12 * n)][term - 1] if period > (12 * n) else 0
            # should be self.rates[period - (12 * n) - 1]
        # for n in self.TERMS:
            # constraint += investments[period - n, term] * self.rates[period - n - 1][term - 1] if period > n else 0
        return constraint

    def _build_mat_constraint(self, period, investments):
        """
        Builds maturity constraint for each investment term in each period.
        > Loops over term and adds to the constraint at each new investment term
        >
        and looking back to the balance invested [period - (12 * n)] periods ago
        """
        constraint = 0
        for n in range(1, self.TERMS + 1):
            constraint += investments[period - (12 * n), n] if period > (12 * n) else 0
        # for n in self.TERMS:
            # constraint += investments[period - n, n] if period > n else 0
        return constraint

    def pyondo(self):
        """
        Linear program that determines maximum interest earned from timing of Investments
        in various terms.
        Considers timing of contributions, timing of expenditures, interest rate projections
        """

        """
        MODEL CONSTANTS
        self._net_flows = Ci - Ei;
        self.bank_rates = BR;
        self.rates = R;
        Minimum Bank Balance = MMB;
        self.opening_balance = OB1
        """

        model = ConcreteModel()

        """
        MODEL DIMENSIONS
        Periods = i;
        Terms = j;  (as in number of years in invmt)
        """
        model.Periods = range(1, (self.periods) + 1)
        model.Terms = range(1, self.TERMS + 1)
        # model.Terms = self.TERMS # will this work with a list???????
        # model.Terms = (i for i in self.TERMS) # will this work with a list???????
        # model.Terms = range(TERMS[0], TERMS[-1], space_between_terms)

        """
        MODEL VARIABLES
        Investments = INV;
        Balance = B;
        PBalance = P;
        Interest = INT;
        """
        model.Investments = Var(model.Periods, model.Terms, within=NonNegativeReals)
        model.TotalInvestment = Var(model.Periods, within=NonNegativeReals)
        model.Balance = Var(model.Periods, within=NonNegativeReals)
        model.PBalance = Var(model.Periods, within=NonNegativeReals)
        model.Maturities = Var(model.Periods, within=NonNegativeReals)
        model.InvestmentInterest = Var(model.Periods, model.Terms, within=NonNegativeReals)
        model.AccountInterest = Var(model.Periods, within=NonNegativeReals)
        model.TotalInterest = Var(model.Periods, within=NonNegativeReals)

        """
        OBJECTIVE FUNCTION
        > maximize interest paid
        > MAX:  sum(INVij * Rij) for i period and j invmt type) plus sum(Bi * BRi)
        """
        def obj_rule(model):
            return (sum(model.TotalInterest[period] for period in model.Periods))

        model.obj = Objective(rule=obj_rule, sense=maximize)

        """
        CONSTRAINTS
        Investment Interest Paid Constraint
        > invINTi = sum of invINTij for all j
        Interest for the monthly period is the sum of the Investments maturing in that period * their interest rate
        """
        model.InvestmentInterest_Constraint = ConstraintList()

        """
        Account Interest Paid Constraint
        > bankINTi = Bi*BRATEi
        """
        model.AccountInterest_Constraint = ConstraintList()

        """
        Total Interest Paid Constraint
        > INTi = invINTi + bankINTi
        """
        model.TotalInterest_Constraint = ConstraintList()

        """
        Maturing Amount Constraint
        > Mi = INVi-12,1 + INVi-24,2 + INVi-36,3 + INVi-48,4 + INVi-60,5
        """
        model.Maturities_Constraint = ConstraintList()

        """
        Minimum Balance constraints
        > sum of INVij for all j <= Pi - MBB
        The sum of investments outstanding in the period must be less than
        the Potential Bank balance for the period less the Minimum required bank balance
        the Potential Bank balance is calculated via the constraint below
        """
        model.MBB_Constraint = ConstraintList()

        """
        Total Investment Constraint
        > totINVi = sum of INVij for all j
        """
        model.TotalInvestment_Constraint = ConstraintList()

        """
        Potential Balance Constraint
        > Pi = Pi-1 - sum of INVi-1j for all j + Ci - Ei + INTi + Mi
        > derived from Pi = Ai-1 + Ci - Ei + INTi + Mi and Ai = Pi - sum of INVij for all j
        The potential bank balance is the prior period potential bank balance plus
        net cash flow for period (contributions, expenditures, interest paid, and invmt maturities are all cash flows)
        """
        model.PBalance_Constraint = ConstraintList()

        """
        Balance Constraint
        > Ai = Pi - sum of INVij for all j
        the current Bank balance is the potential balance less any outstanding investments
        """
        model.Balance_Constraint = ConstraintList()

        for period in model.Periods:
            for term in model.Terms:
                model.InvestmentInterest_Constraint.add(
                    model.InvestmentInterest[period, term] ==
                                    self._build_int_constraint(period, term, model.Investments)
                )
            model.AccountInterest_Constraint.add(
                model.AccountInterest[period] == (model.Balance[period - 1] * (self.bank_rates[period - 1] / 12) if period > 1 else 0)
            )
            model.TotalInterest_Constraint.add(
                model.TotalInterest[period] == (
                    model.AccountInterest[period]
                    + sum(model.InvestmentInterest[period, term] for term in model.Terms)
                    + (self.existing_interest[period] if self.existing_interest else 0)
                )
            )
            model.Maturities_Constraint.add(
                model.Maturities[period] == (
                    self._build_mat_constraint(period, model.Investments)
                    + (self.existing_maturities[period] if self.existing_maturities else 0)
                )
            )
            model.MBB_Constraint.add(
                    sum(model.Investments[period, term] for term in model.Terms) <= model.PBalance[period] - self.MINIMUM_BANK_BALANCE
            )
            model.TotalInvestment_Constraint.add(
                model.TotalInvestment[period] == sum(model.Investments[period, term] for term in model.Terms)
            )
            model.PBalance_Constraint.add(
                model.PBalance[period] == (model.PBalance[period - 1]
                - sum(model.Investments[period - 1, term] for term in model.Terms)
                + model.TotalInterest[period] + self._net_flows[period - 1]
                + model.Maturities[period] if period > 1 else self.opening_balance + self._net_flows[period])
            )
            model.Balance_Constraint.add(model.Balance[period] == model.PBalance[period] - sum(model.Investments[period, term] for term in model.Terms)
            )

        opt = SolverFactory("glpk", executable="/usr/bin/glpsol")

        self.results = opt.solve(model, symbolic_solver_labels=True)
        model.solutions.store_to(self.results)

        self.model = model

        return model

    def results_json(self):
        return self.results.json_repn()

    def result_time(self):
        return self.results_json()["Solver"][0]["Time"]

    def values(self):
        """
        Inputs the solved model returned by Pyondo solver and sorts values for Easy
        bulk upload to Django model
        Use list of dicts with each list index a period in the model
        """
        results = []
        for period in range(1, self.periods + 1):
            dict = {}
            dict["period"] = period
            if period == 1:
                dict["opening_balance"] = self.opening_reserve
            else:
                dict["opening_balance"] = results[period - 2]["closing_balance"]
            dict["contributions"] = self.contributions[period - 1]
            dict["expenditures"] = self.expenditures[period - 1]
            dict["interest"] = self.model.TotalInterest[period].value
            dict["closing_balance"] = (
                                    dict["opening_balance"] + dict["contributions"]
                                    - dict["expenditures"] + dict["interest"]
            )
            dict["bank_balance"] = self.model.Balance[period].value
            dict["current_investments"] = dict["closing_balance"] - dict["bank_balance"]
            dict["maturities"] = self.model.Maturities[period].value
            for term in self.model.Terms:
                dict["term_{}".format(term)] = self.model.Investments[period, term].value
            results.append(dict)
            dict["total_investments"] = self.model.TotalInvestment[period].value

        return results
