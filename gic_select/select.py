import socket, os
from datetime import datetime as dt, date
from urllib.request import urlopen, Request, urlretrieve
import ssl

from bs4 import BeautifulSoup as bs

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from django.db.models.query import QuerySet
from django.db import transaction

from .models import GICs, GICPlan, GICSelect, CDIC, DICO

def update_gics(headless=False):
    # host = "0.0.0.0"  # Bind to 0.0.0.0 to allow external access

    # Set host to externally accessible web server address
    # host = socket.gethostbyname(socket.gethostname())

    print ("initializing GIC Update...")
    if headless:
        # Instantiate the remote WebDriver
        options = Options()
        options.set_headless(headless=True)
        # chrome_options.add_argument('window-size=1920x1080')
        # capabilities = {'browserName': 'chrome', 'javascriptEnabled': True}
        # capabilities.update(chrome_options.to_capabilities())
    elif headless == False:
        options=None
    else:
        raise ValueError("Headless must be Boolean")

    print ("Instantiating WebDriver...")
    chrome = webdriver.Chrome(executable_path=str(os.environ.get('CHROMEDRIVER_PATH')),
                    options=options
    )
    print ("Success")
    url = "http://www.financialpost.com/personal-finance/rates/gic-annual.html"
    print ("Obtaining URL...")
    chrome.get(url)
    print ("Success")
    print ("Updating values...")
    rows = chrome.find_elements_by_tag_name("tr")
    values = []
    for row in rows:
        dct = {}
        if row.get_attribute("class") == "heading":
            pass
        elif row.get_attribute("class") == "heading npTxtLeft":
            break
        else:
            cells = row.find_elements_by_tag_name("td")
            dct["issuer"] = cells[0].text
            dct["date"] = dt.strptime(cells[1].text, "%d %b").replace(year=dt.now().year)
            dct["amount"] = cells[2].text
            for i, cell in enumerate(cells[3:]):
                dct["term"] = i + 1
                dct["rate"] = float(cell.text) / 100
                values.append(dct.copy())

    chrome.quit()
    GICs.objects.bulk_create(GICs(**vals) for vals in values)
    print ("GIC Update complete")

def read_page(url):
    ssl._create_default_https_context = ssl._create_unverified_context

    headers = {}
    headers['User-Agent'] ='Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
    req = Request(url, headers=headers)
    uClient = urlopen(req)
    page = uClient.read()
    uClient.close()

    return page

def cdic_insured():
    url = "http://www.cdic.ca/en/about-di/what-we-cover/Pages/list-members.aspx"
    page = read_page(url)
    soup = bs(page, "html.parser")
    table = soup.find("table", {"class": "pagecontent"})
    rows = table.find_all("tr")

    insureds = [str(row.td.string) for row in rows if row.td.string is not None]
    insureds = [row.strip() for row in insureds if row.strip() != ""]

    return insureds

def dico_insured():
    url = "https://www.dico.com/design/1_1_Eng.html"
    page = read_page(url)
    soup = bs(page, "html.parser")
    table = soup.find("table")
    rows = table.find_all("td")

    insureds = [str(row.string)for row in rows if "width" in row.attrs.keys() and row.attrs["width"] == "100%"]

    return  insureds

@transaction.atomic
def update_cdic_insured():
    """
    Function for updating CDIC model
    """
    print ("Updating CDIC insured list")

    insureds = cdic_insured()

    model_insureds = CDIC.objects.all()

    for model_insured in model_insureds:
        if model_insured.name not in insureds:
            model_insured.delete()

    model_insureds = insureds_list(CDIC)
    for insured in insureds:
        if insured not in model_insureds:
            CDIC.objects.create(name=insured)
    print ("Complete!")

@transaction.atomic
def update_dico_insured():
    """
    Function for updating CDICInsured model
    """
    print ("Updating DICO insured list")
    insureds = dico_insured()

    model_insureds = DICO.objects.all()

    for model_insured in model_insureds:
        if model_insured.name not in insureds:
            model_insured.delete()

    model_insureds = insureds_list(DICO)
    for insured in insureds:
        if insured not in model_insureds:
            DICO.objects.create(name=insured)
    print ("Complete!")

def insureds_list(model):
    return [insured["name"] for insured in model.objects.all().values()]

def all_insureds():
    return list(set(insureds_list(CDIC) + insureds_list(DICO)))

def gic_select(invmts, gics, max_cdic=100000, max_dico=250000):
    """
    Selects potential GIC investments from GIC model
    > Filters most recent date of GIC investments; eliminates any issuers that are not CDIC or DICO insured
    > sorts each term from highest rate to lowest rate
    > Allocates investment amounts to different GICs as follows:
                1) ensure GICs are insured according to Act (see section 115)
                2) limit amount allocated to each issuer to $100K/$250K (as per CDIC/DICO insured limit)
                3) amount allocated is function of available allocation (limit less current allocation)
                4) if any amount is not allocated, it is carried forward to next GIC
                5) when amount = 0, break loop and move on to next invmt term

    Parameters
    -----------
    invmts:     dictionary of terms and amounts to be allocated; provided from first month of Pyondo output
    gics:       GICs model object; should contain only GICs of the most recent date
    max_cdic:   CDIC-insured limit per institution
    max_dico:   DICO-insured limit per institution

    Returns
    -----------
    invmts_by_issuer:   dictionary of issuer names, then 2nd level of investment types and amounts

    ***EDITS***
        1) Needs to bring in Existing investments as well, as they count towards available
    """
    assert isinstance(invmts, dict)
    assert isinstance(gics, QuerySet)
    assert gics.model is GICs

    if len(set(gics.values_list("date"))) > 1:
        raise ValueError("gics object should only contain records from the most recent date")

    cdic_insureds = insureds_list(CDIC)
    dico_insureds = insureds_list(DICO)
    insureds = cdic_insureds + dico_insureds

    issuers = set(gics.values_list("issuer"))
    issuers = [issuer for (issuer, ) in issuers]

    insured_issuers = [issuer for issuer in issuers for insured in insureds if issuer in insured]
    gics = gics.filter(issuer__in=insured_issuers)

    invmts_by_issuer = {issuer: {"term_{}".format(i + 1): 0 for i in range(5)} for issuer in insured_issuers}

    for term, amount in invmts.items():
        gics_term = gics.filter(term=int(term[-1])).order_by("-rate")
        for gic in gics_term:
            max = max_dico if gic.issuer in dico_insureds else max_cdic
            available = max - sum(invmts_by_issuer[gic.issuer].values())

            if amount <= available:
                invmts_by_issuer[gic.issuer][term] += amount
                amount = 0
            else:
                invmts_by_issuer[gic.issuer][term] += available
                amount -= available
            if amount == 0:
                break

    return invmts_by_issuer

@transaction.atomic
def save_gic_selections(selected, gics, gic_plan):
    assert isinstance(selected, dict)
    assert isinstance(gics, QuerySet)
    assert gics.model is GICs

    for issuer, invmts in selected.items():
        for term, amount in invmts.items():
            if amount != 0:
                gic = gics.filter(issuer=issuer, term=int(term[-1])).latest("amount")
                selected = GICSelect.objects.create(gic_plan=gic_plan, gic=gic, amount=amount)

def select_and_save(values, plan):
    assert isinstance(values, dict)

    invmts = {term: value for term, value in values.items() if term[0:4] == "term"}
    last_date = GICs.objects.latest("date").date
    gics = GICs.objects.filter(date=last_date)
    selected = gic_select(invmts, gics)
    gic_plan = GICPlan.objects.create(plan=plan, date=last_date)
    save_gic_selections(selected, gics, gic_plan)
