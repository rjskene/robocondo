from django.shortcuts import render

from django.http import HttpResponse, HttpResponseRedirect

from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import FormView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView
from django.views.generic.base import TemplateView

from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response

from guardian.mixins import PermissionRequiredMixin
from guardian.decorators import permission_required_or_403

from .serializers import StudySerializer, ContributionsSerializer, ExpendituresSerializer, FullStudySerializer
from .models import Study, Contributions, Expenditures
from .forms import RFSForm, ContForm, ExpForm
from .helpers import find_excluded_years, make_cont_and_exp_table

from condo.models import Condo
from investmentplan.models import Plan

@login_required
@permission_required_or_403("reservefundstudy.view_study", (Study, "id", "study_id"))
def study_archive_view(request, **kwargs):
    """
    Archive reserve fund study that User no longer wishes to view
    """
    study = Study.objects.get(id=kwargs["study_id"])
    study.archived = True
    study.save()

    kwargs.pop("study_id", None)
    return redirect(reverse("condo:main", kwargs=kwargs))

@login_required
def conts_and_exps(request, **kwargs):
    """
    Form to input contributions and expenditures for specific Study
    View should be used for both the intial add and for future edits
    """
    study = Study.objects.get(pk=kwargs["rfs_id"])
    excluded_years = find_excluded_years(study)

    if request.method == "POST":
        form_Cont = ContForm(request.POST, excluded_years=excluded_years)
        form_Exp = ExpForm(request.POST, excluded_years=excluded_years)

        if form_Cont.is_valid() and form_Exp.is_valid():
            cont = form_Cont.save(commit=False)
            cont.study = study
            cont.save()
            exp = form_Exp.save(commit=False)
            exp.study = study
            exp.save()

            return redirect(reverse("condo:condo-main", args=(kwargs["condo"], kwargs["condo_id"])))
        else:
            return redirect(reverse("reservefundstudy:conts-exps", args=(kwargs["condo"], kwargs["condo_id"], kwargs["rfs_id"])))

    else:
        # Need to create table inputs dynamically for number of years in Study
        # Find years excluded from max 30 years max_length
        # Then make a list of dictionaries for the table elements

        table = make_cont_and_exp_table(study, ContForm, ExpForm, kwargs)
        context = {
                "first_year": study.first_year,
                "table": table,
        }

        return render(request, "reservefundstudy/conts_exps_add.html",
                    context)

"""
Import below is specifically for combined FullStudy view
"""
from collections import namedtuple
FullStudy = namedtuple("FullStudy", ("study", "contributions", "expenditures"))

class FullStudyViewSet(ViewSet):
    """
    A simple ViewSet for listing a Study with corresponding contributions and expenditures.
    """
    def list(self, request):
        fullstudy = FullStudy(
            study=Study.objects.all(),
            contributions=Contributions.objects.all(),
            expenditures=Expenditures.objects.all()
        )
        serializer = FullStudySerializer(fullstudy, context={"request": request})
        return Response(serializer.data)
