from rest_framework.serializers import HyperlinkedModelSerializer, Serializer, HyperlinkedRelatedField, \
                                        HyperlinkedIdentityField

from .models import HistoricalYieldCurve as HYC, HistoricalOvernightRate as HOR, \
                        InflationRate as INFR, OutputGap as GAP, BOCGICs, \
                        Forecast, BOCGICForecast, Dataset, RAW, PrincipalComponents as PC, \
                        Cointegration as COINT, Technique as TECH, VAR, VARMA, VECM
from .custom_fields import StringArrayField

class BOCGICForecastSerializer(HyperlinkedModelSerializer):
    forecast = HyperlinkedRelatedField(read_only=True, view_name="pyyc:forecast-detail")

    class Meta:
        model = BOCGICForecast
        fields = [field.name for field in BOCGICForecast._meta.get_fields()]

class ForecastSerializer(HyperlinkedModelSerializer):
    bocgicforecast = BOCGICForecastSerializer()
    dataset = HyperlinkedRelatedField(read_only=True, view_name="pyyc:dataset-detail")
    technique = HyperlinkedRelatedField(read_only=True, view_name="pyyc:technique-detail")
    set_rmses = StringArrayField()

    class Meta:
        model = Forecast
        fields = [field.name for field in Forecast._meta.get_fields()]

class DatasetSerializer(HyperlinkedModelSerializer):
    forecast = HyperlinkedRelatedField(read_only=True, view_name="pyyc:forecast-detail")
    cointegration = HyperlinkedRelatedField(read_only=True, view_name="pyyc:cointegration-detail")
    raw = HyperlinkedRelatedField(read_only=True, view_name="pyyc:raw-detail")
    pc = HyperlinkedRelatedField(read_only=True, view_name="pyyc:principal_components-detail")

    class Meta:
        model = Dataset
        fields = [field.name for field in Dataset._meta.get_fields()]

class RAWSerializer(HyperlinkedModelSerializer):
    dataset = HyperlinkedRelatedField(read_only=True, view_name="pyyc:dataset-detail")
    principalcomponents = HyperlinkedRelatedField(read_only=True, view_name="pyyc:principal_components-detail")

    class Meta:
        model = RAW
        fields = [field.name for field in RAW._meta.get_fields()]

class PrincipalComponentsSerializer(HyperlinkedModelSerializer):
    dataset = HyperlinkedRelatedField(read_only=True, view_name="pyyc:dataset-detail")
    raw = HyperlinkedRelatedField(read_only=True, view_name="pyyc:raw-detail")

    class Meta:
        model = PC
        fields = [field.name for field in PC._meta.get_fields()]

class CointegrationSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = COINT
        fields = [field.name for field in COINT._meta.get_fields()]

class TechniqueSerializer(HyperlinkedModelSerializer):
    forecast = HyperlinkedRelatedField(read_only=True, view_name="pyyc:forecast-detail")
    var = HyperlinkedRelatedField(read_only=True, view_name="pyyc:var-detail")
    varma = HyperlinkedRelatedField(read_only=True, view_name="pyyc:varma-detail")
    vecm = HyperlinkedRelatedField(read_only=True, view_name="pyyc:vecm-detail")

    class Meta:
        model = TECH
        fields = [field.name for field in TECH._meta.get_fields()]

class VARSerializer(HyperlinkedModelSerializer):
    technique = HyperlinkedRelatedField(read_only=True, view_name="pyyc:technique-detail")

    class Meta:
        model = VAR
        fields = [field.name for field in VAR._meta.get_fields()]

class VARMASerializer(HyperlinkedModelSerializer):
    technique = HyperlinkedRelatedField(read_only=True, view_name="pyyc:technique-detail")

    class Meta:
        model = VARMA
        fields = [field.name for field in VARMA._meta.get_fields()]

class VECMSerializer(HyperlinkedModelSerializer):
    technique = HyperlinkedRelatedField(read_only=True, view_name="pyyc:technique-detail")

    class Meta:
        model = VECM
        fields = [field.name for field in VECM._meta.get_fields()]
