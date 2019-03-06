from django.shortcuts import render
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib.admin.views.decorators import staff_member_required

from .tasks import update_gics_task

@staff_member_required
def update_gics_view(request, **kwargs):
    result = update_gics_task.delay()
    kwargs["task_id"] = result.task_id

    return redirect(reverse("pyyc:progress", kwargs=kwargs))
