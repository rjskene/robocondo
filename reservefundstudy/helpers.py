

def find_included_years(study):
    return ["year_" + str(x + 1) for x in range(study.years)]

def find_excluded_years(study):
    return ["year_" + str(x) for x in range(study.years + 1, 31)]

def make_cont_and_exp_table(study, form1, form2, kwargs):
    """
    Create table fields for page to add Contributions and Expenditures
    Pass in Query set for a specific study and build list of dicts using zip
    """
    excluded_years = find_excluded_years(study)

    keys = ["year", "cont", "exp"]
    rows = zip(
                range(study.years),
                form1(initial={"study": kwargs["condo"],}, excluded_years=excluded_years),
                form2(initial={"study": kwargs["condo"], }, excluded_years=excluded_years),
    )
    return [ dict(zip(keys,row)) for row in rows ]
