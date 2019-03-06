from django_tables2 import Table

from .models import Forecast

class ForecastsTable(Table):
    class Meta:
        model = Forecast
        template_name = "django_tables2/bootstrap.html"
        fields = (
            "dataset", "technique", "process_time", "total_rmse"
        )
