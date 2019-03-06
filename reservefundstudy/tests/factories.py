from functools import wraps

from factory.django import DjangoModelFactory
from factory import SubFactory

from reservefundstudy.models import Study, Contributions, Expenditures, MAX_STUDY_LENGTH
from condo.tests.factories import CondoFactory

class StudyFactory(DjangoModelFactory):
    class Meta:
        model = Study
        django_get_or_create = ("condo", )

    condo = SubFactory(CondoFactory)
    date = "2014-02-14"
    first_year = 2012
    last_year = 2040
    years = 2040 - 2012 + 1
    opening_balance = 733330
    current = True

def get_kwargs(values):
    prefix = values.pop(0)
    keys = ["{}_year_{}".format(prefix, n) for n in range(1, MAX_STUDY_LENGTH + 1)]
    return dict(zip(keys, contributions))

contributions = [ "cont",
                203000, 210000, 243600,282576,327788,380234,441072,511643,
                593506,688467,702236,716281,730607,745219,760123,775326,
                790832,806649,822782,839238,856022,873143,890606,908418,
                926586,945118,964020,983301,1002967
]

expenditures = [ "exp",
        223841,489283,12293,17139,12602,535790,34068,534489, 13245,314291,
        600049,0,235115,650744,0,4976504,855760,0,5653,605227,3094391,5867,
        560439,352020,272911,3491946,749187,406295,0
]

cont_kwargs = get_kwargs(contributions)
exp_kwargs = get_kwargs(expenditures)

def cont_attrs(cls):
    attr_str = contributions.pop(0)
    keys = ["{}_year_{}".format(attr_str, n) for n in range(1, MAX_STUDY_LENGTH + 1)]
    dct = dict(zip(keys, contributions))
    for key, value in dct.items():
        setattr(cls, key, value)
    return cls

def exp_attrs(cls):
    attr_str = expenditures.pop(0)
    keys = ["{}_year_{}".format(attr_str, n) for n in range(1, MAX_STUDY_LENGTH + 1)]
    dct = dict(zip(keys, expenditures))
    for key, value in dct.items():
        setattr(cls, key, value)
    return cls

# COULDN"T MAKE THIS WORK; IT ALTERED THE CLASS THAT WAS RETURNED
# def create_attrs(values):
#     """
#     Decorator that allows attribute names for factories to be set dynamically
#     The list of names is too long to type out, but it would have been faster
#     than figuring out how to write this!
#     The decorator takes in either contribution or expenditure list, it wraps the
#     the Class to be decorated, sets up the key, creates a dictionary, then uses
#     setattr to set the attribute values for the cls, then returns the cls
#     """
#     def real_decorator(cls):
#         @wraps(cls)
#         def wrapper(*args, **kwargs):
#             attr_str = values.pop(0)
#             keys = ["{}_year_{}".format(attr_str, n) for n in range(1, MAX_STUDY_LENGTH + 1)]
#             dct = dict(zip(keys, contributions)
#             for key, value in dct.items():
#                 setattr(cls, key, value)
#             return cls
#         return wrapper
#     return real_decorator

@cont_attrs
class ContributionsFactory(DjangoModelFactory):

    class Meta:
        model = Contributions
        django_get_or_create = ("study",)

    study = SubFactory(StudyFactory)

@exp_attrs
class ExpendituresFactory(DjangoModelFactory):

    class Meta:
        model = Expenditures
        django_get_or_create = ("study",)

    study = SubFactory(StudyFactory)
