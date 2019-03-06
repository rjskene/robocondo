from rest_framework.serializers import HyperlinkedModelSerializer, Serializer

from .models import Study, Contributions, Expenditures

class StudySerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Study
        fields = [field.name for field in Study._meta.get_fields()]

class ContributionsSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Contributions
        fields = [field.name for field in Contributions._meta.get_fields()]

class ExpendituresSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Expenditures
        fields = [field.name for field in Expenditures._meta.get_fields()]

class FullStudySerializer(Serializer):
    study = StudySerializer(many=True)
    contributions = ContributionsSerializer(many=True)
    expenditures = ExpendituresSerializer(many=True)
