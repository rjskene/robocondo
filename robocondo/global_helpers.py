from copy import deepcopy
from enum import Enum

from django.db.models import Manager, Q
from django.core.exceptions import ObjectDoesNotExist

class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return tuple((x.name, x.value) for x in cls)

class RoCoManager(Manager):
    def get_or_none(self, **kwargs):
        try:
            return self.get(**kwargs)
        except ObjectDoesNotExist:
            return None

    def filter_or_none(self, **kwargs):
        try:
            return self.filter(**kwargs)
        except ObjectDoesNotExist:
            return None

def get_or_none(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except ObjectDoesNotExist:
        return None

def valid_pct(val):
    if val.endswith("%"):
       return float(val[:-1])/100
    else:
       try:
          return float(val)
       except ValueError:
          raise ValidationError(
              _('%(value)s is not a valid pct'),
                params={'value': value},
           )


test_data_1 = {
        "condo_data": {
                        "name": "Toronto Standard Condominium Corporation 1978",
        },
        "reserve_study": {
                                "date": "2014-02-14",
                                "first_year": 2012,
                                "last_year": 2040,
                                "years": 2040 - 2012 + 1,
                                "opening_balance": 733330,
        },
        "contributions": [
                        203000, 210000, 243600,282576,327788,380234,441072,511643,
                        593506,688467,702236,716281,730607,745219,760123,775326,
                        790832,806649,822782,839238,856022,873143,890606,908418,
                        926586,945118,964020,983301,1002967
        ],
        "expenditures": [
                        223841,489283,12293,17139,12602,535790,34068,534489,
                        13245,314291,600049,0,235115,650744,0,4976504,855760,0,
                        5653,605227,3094391,5867,560439,352020,272911,3491946,
                        749187,406295,0
        ],
}

class DBTestSetUp:
    """
    Class to setup database with data for testing; ensures consistency of data used
    between the various test modules
    """
    def __init__(self, data, Condo, Study, Contributions, Expenditures, Plan):
        self.data = deepcopy(data)
        self.condo_data = self.data["condo_data"]
        self.reserve_study = self.data["reserve_study"]
        self.contributions = self.data["contributions"]
        self.expenditures = self.data["expenditures"]
        self.Condo = Condo
        self.Study = Study
        self.Contributions = Contributions
        self.Expenditures = Expenditures
        self.Plan = Plan

    def _make_kwargs(self, model):
        """
        Setup a dictionary for easy use in .create() method for Contributions
        and Expenditures
        """
        keys = [field.name for field in model._meta.get_fields() if field.name != "id"]
        return dict(zip(keys, self.contributions))

    def _create(self, model, kwargs):
        obj, created = model.objects.get_or_create(**kwargs)
        if created:
            return model.objects.get(pk=obj.pk)
        else:
            return obj

    def _create_condo(self):
        self.condo_obj = self._create(self.Condo, self.condo_data)
        return self.condo_obj

    def _create_study(self):
        self.reserve_study["condo"] = self.condo_obj
        self.study_obj = self._create(self.Study, self.reserve_study)
        return self.study_obj

    def _create_conts(self):
        self.contributions.insert(0, self.study_obj)
        conts_kwargs = self._make_kwargs(self.Contributions)
        return self._create(self.Contributions, conts_kwargs)

    def _create_exps(self):
        self.expenditures.insert(0, self.study_obj)
        exps_kwargs = self._make_kwargs(self.Expenditures)
        return self._create(self.Expenditures, exps_kwargs)

    def _create_plan(self):
        return self._create(self.Plan, {"study": self.study_obj})

    def study_setup(self):
        return self._create_condo(), self._create_study(), self._create_conts(), self._create_exps()

    def full_setup(self):
        return self._create_condo(), self._create_study(), self._create_conts(), \
                self._create_exps(), self._create_plan()
