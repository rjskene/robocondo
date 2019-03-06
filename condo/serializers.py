from rest_framework.serializers import HyperlinkedModelSerializer

from .models import Condo

class CondoSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Condo
        fields = (
                    "name", "date_added", "date_modified"
        )
