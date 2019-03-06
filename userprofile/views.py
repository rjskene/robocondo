from django.shortcuts import render

from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic.list import ListView

from condo.models import Condo

class DashboardView(LoginRequiredMixin, ListView):

    model = Condo
    template_name = 'userprofile/dashboard.html'

    def get_queryset(self):
        self.username = self.request.user.username
        return Condo.objects.all()
