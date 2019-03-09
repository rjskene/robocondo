import math

from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.views.generic.list import ListView

from rest_framework.viewsets import ModelViewSet
from guardian.shortcuts import get_objects_for_user

from .serializers import UserSerializer
from .forms import SignUpForm, LoginForm

from condo.models import Condo
from rcdemo.forms import RFSDemoForm
from rcdemo.tasks import rcdemo_task
from investmentplan.converter import Converter

def login_view(request):
    context = {}
    if request.method == "POST":
        form = LoginForm(request.POST) if "signin_form" in request.POST else None
        demo_form = RFSDemoForm(request.POST, request.FILES) if "demo_form" in request.POST else None

        if form is not None and form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return redirect(reverse("accountmanager:dashboard", args=(request.user.username,)))
            else:
                print ("User was not authenticated")
        elif demo_form is not None and demo_form.is_valid():
            conv_kwargs = demo_form.save()

            result = rcdemo_task.delay(**conv_kwargs, naive_rates=True)
            return redirect(reverse("rcdemo:progress", args=(result.task_id, )))
        else:
            messages.error(request, "The Form was completed incorrectly.", extra_tags="error_warning")
            return redirect(reverse("accountmanager:login"))
    else:
        form = LoginForm()
        context["demo_form"] = RFSDemoForm()
    return render(request, "accountmanager/signin.html", context)

def signup(request):
    """
    User Sign Up page
    """
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=raw_password)
            if user:
                login(request, user)
                return redirect(reverse("accountmanager:dashboard", args=(request.user.username,)))
    else:
        form = SignUpForm()
    return render(request, "accountmanager/signup.html", {"form": form})

@login_required
def userpage(request):
    """
    LOGIN_REDIRECT_URL is routed here so that the setting can have a static value
    Then redirects to dynamic dashboard for the current user
    """
    return redirect(reverse("userprofile:dashboard", args=(request.user.username,)))

class DashboardView(LoginRequiredMixin, ListView):

    model = Condo
    template_name = "accountmanager/dashboard.html"

    def get_queryset(self):
        self.username = self.request.user.username
        condos = get_objects_for_user(self.request.user, "condo.view_condo")
        return condos

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        condos = list(get_objects_for_user(self.request.user, "condo.view_condo"))
        rows = math.ceil(len(condos) / 3)
        print (rows)
        sorted_condos = []
        if rows == 1:
            sorted_condos.append(condos)
        else:
            for row in range(rows - 1):
                sorted_condos.append([])
                for i in range(3):
                    sorted_condos[row].append(condos.pop())
                    print (sorted_condos)
            sorted_condos.append(condos)
        context["rows"] = rows
        context["condos"] = sorted_condos
        print (sorted_condos)
        return context

class UserViewSet(ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
