from django.urls import include, path

from django.contrib import admin
from django.contrib.auth import views as auth_views

from rest_framework.routers import DefaultRouter

from accountmanager.urls import router as user_router
from condo.urls import router as condo_router
from reservefundstudy.urls import router as study_router
from investmentplan.urls import router as plan_router
# from pyyc.urls import router as pyyc_router

from accountmanager.views import login_view

# api_router = DefaultRouter()
# api_router.registry.extend(user_router.registry)
# api_router.registry.extend(condo_router.registry)
# api_router.registry.extend(study_router.registry)
# api_router.registry.extend(plan_router.registry)
#
# api_pyyc_router = DefaultRouter()
# api_pyyc_router.registry.extend(pyyc_router.registry)

urlpatterns = [
                path("", login_view , name="login"),
                path("", include("accountmanager.urls")),
                path("", include("userprofile.urls")),
                path("", include("condo.urls")),
                path("", include("reservefundstudy.urls")),
                path("", include("investmentplan.urls")),
                path("", include("pyyc.urls")),
                path("", include("gic_select.urls")),
                path("", include("rcdemo.urls")),
                # path("api/", include(api_router.urls)),
                path("admin/", admin.site.urls),
]
