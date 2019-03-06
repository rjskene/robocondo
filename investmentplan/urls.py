from django.urls import path, include
from django.urls import reverse

from django.contrib.auth import views as auth_views

from rest_framework.routers import DefaultRouter

from .views import PlanView, run_robocondo, progress_view, get_progress

app_name = "investmentplan"

"""
Setup Router for Plan and Forecast API. There is no separate URL path in the app.urls
Instead, the URL path is incorporated with all other app APIs at the project.urls level
"""
router = DefaultRouter()

urlpatterns = [
                path("<condo>-<condo_id>/rfs-<rfs_id>/plan-<plan_id>/main", PlanView.as_view(), name="plan-main"),
                path("<condo>-<condo_id>/rfs-<rfs_id>/run-robocondo", run_robocondo, name="run-robocondo"),
                path("<condo>-<condo_id>/rfs-<rfs_id>/robocondo-progress/<task_id>", progress_view, name="progress"),
                path("<condo>-<condo_id>/rfs-<rfs_id>/robocond-get-progress/<task_id>", get_progress, name="get-progress")
]
