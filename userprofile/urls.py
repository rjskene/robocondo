from django.urls import path, include
from django.urls import reverse

from django.contrib.auth import views as auth_views

from .views import DashboardView

app_name = "userprofile"

urlpatterns = [
                # path("dashboard/<username>/", DashboardView.as_view(), name="dashboard"),
]
