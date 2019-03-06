from factory.django import DjangoModelFactory
from factory import SubFactory

from investmentplan.models import Plan
from reservefundstudy.tests.factories import StudyFactory

class PlanFactory(DjangoModelFactory):
    class Meta:
        model = Plan
        django_get_or_create = ("study", )

    study = SubFactory(StudyFactory)
