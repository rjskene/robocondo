from django import template

from pyyc.models import Dataset, Technique

register = template.Library()

@register.filter
def inf(dataset):
    if not isinstance(dataset, Dataset):
        raise ValueError("dataset must be an instance of Dataset model")
    else:
        return dataset.inf()

@register.filter
def gap(dataset):
    if not isinstance(dataset, Dataset):
        raise ValueError("dataset must be an instance of Dataset model")
    else:
        return dataset.output_gap()

@register.filter
def n_diffs(dataset):
    if not isinstance(dataset, Dataset):
        raise ValueError("dataset must be an instance of Dataset model")
    else:
        return dataset.n_diffs()
