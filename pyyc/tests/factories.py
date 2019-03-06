# from factory.django import DjangoModelFactory
# from factory import SubFactory
#
# from investmentplan.models import Plan
# from reservefundstudy.tests.factories import StudyFactory
#
# class PlanFactory(DjangoModelFactory):
#     class Meta:
#         model = Plan
#
#     study = SubFactory(StudyFactory)
#
# class PlanDupFactory(DjangoModelFactory):
#     class Meta:
#         django_get_or_create = ("study", )
