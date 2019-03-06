from django.urls import path, include
from django.urls import reverse

from django.contrib.auth import views as auth_views

from rest_framework.routers import DefaultRouter

from .views import login_view, userpage, signup, DashboardView, UserViewSet

app_name = "accountmanager"

"""
Setup Router for User API. There is no separate URL path in the app.urls
Instead, the URL path is incorporated with all other app APIs at the project.urls level
"""
router = DefaultRouter()
router.register("users", UserViewSet)

urlpatterns = [
                path("login/", login_view , name="login"),
                path("logout/", auth_views.LogoutView.as_view(), name="logout"),
                path("signup/", signup, name="signup"),
                path("dashboard/<username>/", DashboardView.as_view(), name="dashboard"),
]
