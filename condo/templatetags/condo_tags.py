from django import template

register = template.Library()

titles = {"invmt": "Investment", "study": "Study", "account": "Account"}

@register.inclusion_tag("condo/update_modal.html")
def update_modal(type, form_number, form):
    id = "update" + type + "modal" + form_number
    title = "Update " + type if type != "invmt" else "Investment"
    title_id = "update" + type + "title"
    form_name = "update_" + type + "_form" + form_number

    return { "id": id, "title": title, "title_id": title_id,
            "form_name": form_name, "form": form
    }

@register.inclusion_tag("condo/create_modal.html")
def create_modal(type, form):
    id = "create" + type + "modal"
    title = titles[type]
    title_id = "create" + type + "title"
    form_name = "create_" + type + "_form"

    return { "id": id, "title": title, "title_id": title_id,
            "form_name": form_name, "form": form
    }

@register.inclusion_tag("condo/archive_modal.html")
def archive_modal(type, form_number, condo, condo_id, model_id):

    id = "archive" + type + "modal" + form_number
    title = titles[type]
    title_id = "update" + type + "title"
    form_name = "update_" + type + "_form" + form_number
    url_reverse = ("condo:" if type != "study" else "reservefundstudy:") + type + "-archive"

    return {
            "id": id, "title": title, "title_id": title_id,
            "form_name": form_name, "url_reverse": url_reverse,
            "condo": condo, "condo_id": condo_id, "model_id": model_id
    }
