from django.urls import path

from .views import demo_progress_view, demo_get_progress, DemoPlanView

app_name = "rcdemo"

urlpatterns = [
                path("demo/<task_id>", DemoPlanView.as_view(), name="plan"),
                path("demo/progress/<task_id>", demo_progress_view, name="progress"),
                path("demo/get-progress/<task_id>", demo_get_progress, name="get-progress")
]
