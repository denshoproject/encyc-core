from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
from operator import itemgetter
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import ring

from encyc import config
from encyc import http


NON_ARTICLE_PAGES = ['about', 'categories', 'contact', 'contents', 'search',]
TIMEOUT = float(config.MEDIAWIKI_API_TIMEOUT)


def status_code():
    """Return HTTP status code from GET-ing the Mediawiki API
    
    @returns: (int, str)
    """
    r = http.get(config.MEDIAWIKI_API)
    return r.status_code,r.reason

def api_login_round1(lgname, lgpassword):
    url = '%s?action=login&format=xml' % (config.MEDIAWIKI_API)
    domain = urlparse(url).netloc
    if domain.find(':') > -1:
        domain = domain.split(':')[0]
    payload = {'lgname':lgname, 'lgpassword':lgpassword}
    r = http.post(url, data=payload, timeout=TIMEOUT)
    if '401 Authorization Required' in r.text:
        raise Exception('401 Authorization Required')
    soup = BeautifulSoup(
        r.text,
        features='html.parser'
    )
    login = soup.find('login')
    result = {
        'result': login['result'],
        'domain': domain,
        'cookieprefix': login['cookieprefix'],
        'sessionid': login['sessionid'],
        'token': login['token'],
        }
    return result

def api_login_round2(lgname, lgpassword, result):
    url = '%s?action=login&format=xml' % (config.MEDIAWIKI_API)
    domain = urlparse(url).netloc
    if domain.find(':') > -1:
        domain = domain.split(':')[0]
    payload = {'lgname':lgname, 'lgpassword':lgpassword, 'lgtoken':result['token'],}
    cookies = {'%s_session' % result['cookieprefix']: result['sessionid'], 'domain':domain,}
    r = http.post(url, data=payload, cookies=cookies, timeout=TIMEOUT)
    if 'WrongPass' in r.text:
        raise Exception('Bad MediaWiki API credentials')
    soup = BeautifulSoup(
        r.text,
        features='html.parser'
    )
    login = soup.find('login')
    result = {
        'result': login['result'],
        'lguserid': login['lguserid'],
        'lgusername': login['lgusername'],
        'lgtoken': login['lgtoken'],
        'cookieprefix': login['cookieprefix'],
        'sessionid': login['sessionid'],
        'domain': domain,
        'cookies': r.cookies,
        }
    return result

def api_login():
    """Tries to perform a MediaWiki API login.
    
    Returns a set of MediaWiki cookies for use by subsequent
    HTTP requests.
    """
    cookies = []
    lgname = config.MEDIAWIKI_API_USERNAME
    lgpassword = config.MEDIAWIKI_API_PASSWORD
    round1 = api_login_round1(lgname, lgpassword)
    round2 = api_login_round2(lgname, lgpassword, round1)
    if round2.get('result',None) \
           and (round2['result'] == 'Success') \
           and round2.get('cookies',None):
        cookies = round2['cookies']
    return cookies

def api_logout():
    url = '%s?action=logout' % (config.MEDIAWIKI_API)
    headers = {'content-type': 'application/json'}
    r = http.post(url, headers=headers, timeout=TIMEOUT)

def _all_pages(r_text):
    """
    @param r_text: str Text of API call
    @returns: list of dicts
    """
    pages = []
    response = json.loads(r_text)
    if response and response['query'] and response['query']['pages']:
        for id in response['query']['pages']:
            page = response['query']['pages'][id]
            page['timestamp'] = page['revisions'][0]['timestamp']
            page.pop('revisions')
            pages.append(page)
    return pages

@ring.redis(config.CACHE, coder='json')
def all_pages():
    """Returns a list of all pages, with timestamp of latest revision.
    @returns: list of dicts
    """
    pages = []
    cookies = api_login()
    # all articles
    LIMIT=5000
    url = '%s?action=query&generator=allpages&prop=revisions&rvprop=timestamp&gaplimit=5000&format=json' % (config.MEDIAWIKI_API)
    r = http.get(url, headers={'content-type':'application/json'}, cookies=cookies, timeout=TIMEOUT)
    if r.status_code == 200:
        pages = _all_pages(r.text)
    api_logout()
    return pages

def _articles_a_z(published_pages, author_pages, nonarticle_titles):
    """
    @param published_pages: list of dicts
    @param author_pages: list of strs
    @param nonarticle_titles: list of strs
    @returns: list of dicts
    """
    author_titles = [page['title'] for page in author_pages]
    pages = []
    for page in published_pages:
        if ('Category' not in page['title']) \
        and (page['title'] not in author_titles) \
        and (page['title'] not in nonarticle_titles) \
        and (page['title'] not in pages):
            pages.append(page)
    return pages
    
@ring.redis(config.CACHE, coder='json')
def articles_a_z():
    """Returns a list of published article titles arranged A-Z.
    @returns: list of dicts
    """
    titles = _articles_a_z(
        category_members('Published', namespace_id=namespaces_reversed()['Default']),
        published_authors(),
        NON_ARTICLE_PAGES
    )
    return titles

@ring.redis(config.CACHE, coder='json')
def articles_by_category():
    """Returns list of published articles grouped by category.
    @returns: (list of strs, dict of article dicts per category)
    """
    categories = []
    titles_by_category = {}
    published = [page['title'] for page in published_pages()]
    cat_titles = [page['title'] for page in category_article_types()]
    for category in cat_titles:
        category = category.replace('Category:','')
        # TODO fix this, this is bad
        titles = [
            page
            for page in category_members(
                    category, namespace_id=namespaces_reversed()['Default']
            )
            if page['title'] in published
        ]
        if titles:
            categories.append(category)
            titles_by_category[category] = titles
    return categories,titles_by_category

def article_next(title):
    """Returns the title of the next article in the A-Z list.
    @param title: str
    @returns: bool
    """
    titles = [page['title'] for page in articles_a_z()]
    try:
        return titles[titles.index(title) + 1]
    except:
        pass
    return None
    
def article_prev(title):
    """Returns the title of the previous article in the A-Z list.
    @param title: str
    @returns: bool
    """
    titles = [page['title'] for page in articles_a_z()]
    try:
        return titles[titles.index(title) - 1]
    except:
        pass
    return None

def author_articles(title):
    """
    @param title: str
    @returns: list of strs
    """
    return what_links_here(title)

def _category_members(r_text):
    """
    @param r_text: str
    @returns: list of dicts
    """
    pages = []
    response = json.loads(r_text)
    if response and response['query'] and response['query']['categorymembers']:
        for page in response['query']['categorymembers']:
            page['sortkey'] = page['sortkeyprefix']
            page.pop('sortkeyprefix')
            if page['title'] and not page['sortkey']:
                page['sortkey'] = page['title']
            if page['sortkey']:
                page['sortkey'] = page['sortkey'].lower()
            pages.append(page)
        pages = sorted(pages, key=itemgetter('sortkey'))
    return pages

@ring.redis(config.CACHE, coder='json')
def category_members(category_name, namespace_id=None):
    """Returns titles of pages with specified Category: tag.
    
    NOTE: Rather than just returning a list of title strings, this returns
    a list of _dicts_ containing namespace id, title, and sortkey.
    This is so certain views (e.g. Contents A-Z can grab the first letter
    of the title (or sortkey) to use for grouping purposes.
    
    @param category_name: str
    @param namespace_id: str
    @returns: list of dicts
    """
    cookies = api_login()
    LIMIT = 5000
    url = '%s?format=json&action=query&list=categorymembers&cmsort=sortkey&cmprop=ids|sortkeyprefix|title&cmtitle=Category:%s&cmlimit=5000' % (config.MEDIAWIKI_API, category_name)
    if namespace_id != None:
        url = '%s&gcmnamespace=%s' % (url, namespace_id)
    r = http.get(url, headers={'content-type':'application/json'}, cookies=cookies, timeout=TIMEOUT)
    if r.status_code == 200:
        pages = _category_members(r.text)
    api_logout()
    return pages

def category_article_types():
    """Returns list of subcategories underneath 'Article'.
    @returns: list of dicts
    """
    titles = [page for page in category_members('Articles')]
    return titles
def category_authors():
    """
    @returns: list of dicts
    """
    titles = [page for page in category_members('Authors')]
    return titles
def category_supplemental():
    """
    @returns: list of dicts
    """
    titles = [page for page in category_members('Supplemental_Materials')]
    return titles

def is_article(title):
    """
    @param title: str
    @returns: bool
    """
    titles = [page['title'] for page in published_pages()]
    if title in titles:
        return True
    return False

def is_author(title):
    """
    @param title: str
    @returns: bool
    """
    for page in category_authors():
        if title == page['title']:
            return True
    return False

def _namespaces(r_text):
    """
    @param r_text: str
    @returns: dict
    """
    namespaces = {}
    response = json.loads(r_text)
    if response and response['query'] and response['query']['namespaces']:
        for n in response['query']['namespaces']:
            ns = response['query']['namespaces'][n]
            nsid = ns['id']
            if ns.get('canonical',None):
                nsname = ns['canonical']
            else:
                nsname = ns['content']
            if not nsname:
                nsname = u'Default'
            namespaces[nsid] = nsname
    return namespaces

@ring.redis(config.CACHE, coder='json')
def namespaces():
    """Returns dict of namespaces and their codes.
    @returns: dict
    """
    url = '%s?action=query&meta=siteinfo&siprop=namespaces|namespacealiases&format=json' % (config.MEDIAWIKI_API)
    r = http.get(url, headers={'content-type':'application/json'}, timeout=TIMEOUT)
    if r.status_code == 200:
        namespaces = _namespaces(r.text)
    return namespaces

def namespaces_reversed():
    """Returns dict of namespaces and their codes, organized by name.
    @returns: dict
    """
    nspaces = {}
    namespaces_codes = namespaces()
    for key,val in namespaces_codes.items():
        nspaces[val] = key
    return nspaces

def _page_categories(whitelist, r_text):
    """
    @param whitelist: list of dicts
    @param r_text: str
    @returns: list of strs
    """
    categories = []
    article_categories = [c['title'] for c in whitelist]
    response = json.loads(r_text)
    ids = []
    if response and response['query'] and response['query']['pages']:
        ids = [id for id in response['query']['pages'].keys()]
    for id in ids:
        for cat in response['query']['pages'][id]['categories']:
            category = cat['title']
            if article_categories and (category in article_categories):
                categories.append(category.replace('Category:', ''))
    return categories
    
@ring.redis(config.CACHE, coder='json')
def page_categories(title, whitelist=[]):
    """Returns list of article subcategories the page belongs to.
    @returns: list of strs
    """
    url = '%s?format=json&action=query&prop=categories&titles=%s' % (config.MEDIAWIKI_API, title)
    r = http.get(url, headers={'content-type':'application/json'}, timeout=TIMEOUT)
    if r.status_code == 200:
        if not whitelist:
            whitelist = category_article_types()
        categories = _page_categories(whitelist, r.text)
    return categories

def _published_pages(allpages, all_published_pages):
    """
    @param allpages: list of dicts
    @param all_published_pages: list of dicts
    @returns: list of dicts
    """
    # published_article_ids
    pids = [page['pageid'] for page in all_published_pages]
    pages = []
    for page in allpages:
        if page['pageid'] in pids:
            if page.get('revisions') \
            and page['revisions'][0].get('timestamp') \
            and not page.get('timestamp'):
                page['timestamp'] = page['revisions'][0]['timestamp']
            pages.append(page)
    return pages
    
@ring.redis(config.CACHE, coder='json')
def published_pages(cached_ok=True):
    """Returns a list of *published* articles (pages), with timestamp of latest revision.
    @param cached_ok: boolean Whether cached results are OK.
    @returns: list of dicts
    """
    pages = _published_pages(
        all_pages(),
        category_members('Published', namespace_id=namespaces_reversed()['Default'])
    )
    return pages

def _published_authors(publishedpages, categoryauthors):
    """
    @param publishedpages: list of dicts
    @param categoryauthors: list of dicts
    @returns: list of dicts
    """
    titles = []
    for page in publishedpages:
        if page['title'] not in titles:
            titles.append(page['title'])
    authors = [
        page
        for page in categoryauthors
        if page['title'] in titles
    ]
    return authors

@ring.redis(config.CACHE, coder='json')
def published_authors(cached_ok=True):
    """Returns a list of *published* authors (pages), with timestamp of latest revision.
    @param cached_ok: boolean Whether cached results are OK.
    @returns: list of dicts
    """
    authors = _published_authors(
        published_pages(),
        category_authors()
    )
    return authors

def _whatlinkshere(publishedpages, r_text):
    """
    @param publishedpages: list of dicts
    @param r_text: str
    @returns: list of strs
    """
    titles = []
    published = [page['title'] for page in publishedpages]
    response = json.loads(r_text)
    if response and response['query'] and response['query']['backlinks']:
        titles = [
            backlink['title']
            for backlink in response['query']['backlinks']
            if backlink['title'] in published
        ]
    return titles
    
@ring.redis(config.CACHE, coder='json')
def what_links_here(title):
    """Returns titles of published pages that link to this one.
    @param title: str
    @returns: list of strs
    """
    url = '%s?format=json&action=query&list=backlinks&bltitle=%s&bllimit=5000' % (config.MEDIAWIKI_API, title)
    r = http.get(url, headers={'content-type':'application/json'}, timeout=TIMEOUT)
    if r.status_code == 200:
        titles = _whatlinkshere(published_pages(), r.text)
    return titles
