from django.core.exceptions import ObjectDoesNotExist

from .tasks import analysis_forecast_task
from .models import Analysis, Forecast
from condo.models import Condo
from reservefundstudy.models import Study
from pyyc.models import Forecast as YCForecast
from investmentplan.converter import Converter as IPConverter

def analysis():
    """
    Uses preselected forecasted yield curves from PYYC and studies
    Generates forecast for each pair of curves and studies
    """
    curve_ids = [3250, 3262, 3259, 3261, 3289, 3287, 3299]
    study_ids = [55, 35, 57, 59]

    try:
        group = Forecast.objects.latest("group").group
    except ObjectDoesNotExist:
        group = 0
    for i, id in enumerate(study_ids):
        for j, curve_id in enumerate(curve_ids):
            group += 1
            study = Study.objects.get(id=id)
            result = analysis_forecast_task.delay(study.condo.id, study.id, group, curve_id)

class Converter(IPConverter):

    def __init__(self, curve_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current = YCForecast.objects.get(id=curve_id)

    def _set_rates(self):
        bank_rates, rates = self.current.bocgicforecast.split_rates(length=len(self.dates))
        bank_rates = [rate - self.spread for rate in bank_rates]
        bank_rates = self._make_zero(bank_rates)
        rates = [self._make_zero(period) for period in rates]

        return bank_rates, rates
