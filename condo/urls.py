from django.urls import path, include
from django.urls import reverse

from django.contrib.auth import views as auth_views

from rest_framework.routers import DefaultRouter
from .views import condo_main, invmt_archive_view, account_archive_view, \
                CondoAssign, CondoCreate, CondoViewSet

app_name = "condo"

"""
Setup Router for User API. There is no separate URL path in the app.urls
Instead, the URL path is incorporated with all other app APIs at the project.urls level
"""
router = DefaultRouter()
router.register("condos", CondoViewSet)

urlpatterns = [
                path("condo-create/", CondoCreate.as_view(), name="create"),
                path("condo-assign/", CondoAssign.as_view(), name="assign"),
                path("<condo>-<condo_id>/", condo_main, name="main"),
                path("<condo>-<condo_id>/investment-<invmt_id>/delete", invmt_archive_view, name="invmt-archive"),
                path("<condo>-<condo_id>/account-<account_id>/delete", account_archive_view, name="account-archive")
]
