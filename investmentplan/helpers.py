from datetime import datetime as dt, timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone

from django.db.models import Sum

def int_to_date(year):
    return dt(year, 1, 1)

def find_date(year, period):
    return timezone.make_aware(int_to_date(year) + relativedelta(months=period - 1) + relativedelta(months=1,days=-1))

def find_period(year, date):
    delta = relativedelta(date, find_date(year, 1))
    return delta.years * 12 + delta.months

def find_dates(first_year, rng):
    """
    Find dates that correspond to the Reserve Fund Study and the number of periods in the Plan
    Make the date timezone sensitive
    """
    return [find_date(first_year, period) for period in range(1, rng + 1)]

def current_investments(forecast, terms):
    """
    Find the current outstanding investments for each category of investment
    Returns a dictionary of lists for each investment over the time period
    Takes in given queryset, filters a new queryset for each row that is the aggregate Sum
    of all the new investments in the period.
    Can be adjusted dynamically for number of terms.
    """
    from .models import Forecast

    dct = {}
    for term in range(1, terms + 1):
        key = "term_{}".format(term)
        dct[key] = []
        periods = term * 12
        for row in forecast:
            last_period = 1 if row.period <= periods else row.period - periods + 1
            new_invmts = (
                Forecast.objects.
                filter(plan=row.plan, period__gte=last_period, period__lte=row.period).
                aggregate(Sum(key))[key + "__sum"]
            )
            dct[key].append(new_invmts)
            dct[key] = dct[key][::-1]
    return dct
