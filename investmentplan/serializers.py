from rest_framework.serializers import HyperlinkedModelSerializer, Serializer

from .models import Plan, Forecast

class PlanSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Plan
        fields = [field.name for field in Plan._meta.get_fields() if field.name != "forecast"]

class ForecastSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Forecast
        fields = [field.name for field in Forecast._meta.get_fields() if field.name != "study"]
