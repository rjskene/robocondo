from django import template

register = template.Library()

@register.inclusion_tag("pyyc/progress_bar.html")
def get_progress_router(type, form_number, form):
    id = "update" + type + "modal" + form_number
    title = "Update " + type if type != "invmt" else "Investment"
    title_id = "update" + type + "title"
    form_name = "update_" + type + "_form" + form_number

    return { "id": id, "title": title, "title_id": title_id,
            "form_name": form_name, "form": form
    }
