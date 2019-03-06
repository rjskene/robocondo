from django.urls import path, include
from django.urls import reverse

from django.contrib.auth import views as auth_views

from rest_framework.routers import DefaultRouter

from .views import main_view, progress_view, get_progress_view, ForecastViewSet, BOCGICForecastViewSet, DatasetViewSet, RAWViewSet, \
                    PrincipalComponentsViewSet, TechniqueViewSet, VARViewSet, VARMAViewSet, \
                    VECMViewSet, CointegrationViewSet, update_data_view, run_forecasts

app_name = "pyyc"

# """
# Setup Router for PYYC API.
# """
# router = DefaultRouter()
# router.register("forecast", ForecastViewSet, base_name="forecast")
# router.register("gic_forecast", BOCGICForecastViewSet, base_name="gic_forecast")
# router.register("dataset", DatasetViewSet, base_name="dataset")
# router.register("raw", RAWViewSet, base_name="raw")
# router.register("principal_components", PrincipalComponentsViewSet, base_name="principal_components")
# router.register("technique", TechniqueViewSet)
# router.register("var", VARViewSet, base_name="var")
# router.register("varma", VARMAViewSet, base_name="varma")
# router.register("vecm", VECMViewSet)
# router.register("cointegration", CointegrationViewSet, base_name="cointegration")

urlpatterns = [
                path(app_name + "/", main_view, name="main"),
                path(app_name + "/progress/<task_id>", progress_view, name="progress"),
                path(app_name + "/get-progress/<task_id>", get_progress_view, name="get-progress"),
                path(app_name + "/update-data/", update_data_view, name="update-data"),
                path(app_name + "/run_forecasts/", run_forecasts, name="run-forecasts"),
                # path(app_name + "/api/", include(router.urls)),
]
