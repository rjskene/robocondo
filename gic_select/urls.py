from django.urls import path, include
from django.urls import reverse

from django.contrib.auth import views as auth_views

from rest_framework.routers import DefaultRouter

from .views import update_gics_view

app_name = "gic_select"

"""
Setup Router for gic_select API.
"""
router = DefaultRouter()
# router.register("forecast", ForecastViewSet, base_name="forecast")

urlpatterns = [
                path(app_name + "/update-gic-data/", update_gics_view, name="update-gics"),
]
