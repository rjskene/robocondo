from django.urls import path, include
from django.urls import reverse

from django.contrib.auth import views as auth_views

from rest_framework.routers import DefaultRouter

from .views import study_archive_view, conts_and_exps, FullStudyViewSet

app_name = "reservefundstudy"

"""
Setup Router for Study API. There is no separate URL path in the app.urls
Instead, the URL path is incorporated with all other app APIs at the project.urls level
"""
router = DefaultRouter()
router.register("fullstudies", FullStudyViewSet, base_name="fullstudies")

urlpatterns = [
                path("<condo>-<condo_id>/rfs-<study_id>/delete/", study_archive_view, name="study-archive"),
                path("<condo>-<condo_id>/rfs-<study_id>/conts-and-exps-add/", conts_and_exps , name="conts-exps"),
]
