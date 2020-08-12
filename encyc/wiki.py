from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
from operator import itemgetter
import re
from typing import List, Set, Dict, Tuple, Optional, Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import mwclient
import ring

from encyc import config
from encyc import http


NON_ARTICLE_PAGES = ['about', 'categories', 'contact', 'contents', 'search',]
TIMEOUT = float(config.MEDIAWIKI_API_TIMEOUT)


# TODO encyc.cli
def status_code() -> Tuple[int,str]:
    """Return HTTP status code from GET-ing the Mediawiki API
    
    @returns: (int, str)
    """
    r = http.get(config.MEDIAWIKI_API)
    return r.status_code,r.reason


SORTKEY_PROG = re.compile(r'DEFAULTSORT:(\w+)')

class Page(mwclient.page.Page):

    def __init__(self, page):
        for key,val in page.__dict__.items():
            setattr(self, key, val)

    def __repr__(self):
        return '<%s.%s "%s">' % (
            self.__module__,
            self.__class__.__name__,
            self.name
        )

    def sortkey(self):
        """Contents of DEFAULTSORT tag or the title
        """
        match = re.search(pattern, page.text())
        if match:
            return match.groups()[0]
        return page.name


class Author(Page):

    def __init__(self, page):
        for key,val in page.__dict__.items():
            setattr(self, key, val)

    def __repr__(self):
        return '<%s.%s "%s">' % (
            self.__module__,
            self.__class__.__name__,
            self.name
        )


class MediaWiki():

    def __init__(self):
        self.mw = MediaWiki._login()

    @staticmethod
    def _login():
        """Get an initialconnection to the wiki.
        """
        logging.debug('initializing')
        if config.MEDIAWIKI_HTTP_USERNAME and config.MEDIAWIKI_HTTP_PASSWORD:
            logging.debug('http passwd')
            wiki = mwclient.Site(
                host=config.MEDIAWIKI_HOST,
                scheme=config.MEDIAWIKI_SCHEME,
                path='/',
                httpauth=(
                    config.MEDIAWIKI_HTTP_USERNAME,
                    config.MEDIAWIKI_HTTP_PASSWORD
                ),
                retry_timeout=5, max_retries=3,
            )
        else:
            logging.debug('no http passwd')
            wiki = mwclient.Site(
                host=config.MEDIAWIKI_HOST,
                scheme=config.MEDIAWIKI_SCHEME,
                path='/',
                retry_timeout=5, max_retries=3,
            )
        logging.debug(wiki)
        logging.debug('logging in')
        wiki.login(
            username=config.MEDIAWIKI_USERNAME,
            password=config.MEDIAWIKI_PASSWORD
        )
        logging.debug(wiki)
        logging.debug('done')
        return wiki

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
    
@ring.redis(config.CACHE, coder='json')
def articles_a_z() -> List[str]:
    """Returns a list of published article titles arranged A-Z.
    @returns: list of encyc.wiki.Page
    """
    w = MediaWiki()
    authors = [page.name for page in w.mw.categories['Authors']]
    return sorted([
        page.name for page in published_pages()
        if page.name not in authors
    ])

# DONE encyc.models.legacy
def article_next(title: str) -> List[str]:
    """Returns the title of the next article in the A-Z list.
    @param title: str
    @returns: bool
    """
    titles = articles_a_z()
    try:
        return titles[titles.index(title) + 1]
    except:
        pass
    return []
    
# DONE encyc.models.legacy
def article_prev(title: str) -> List[str]:
    """Returns the title of the previous article in the A-Z list.
    @param title: str
    @returns: bool
    """
    titles = articles_a_z()
    try:
        return titles[titles.index(title) - 1]
    except:
        pass
    return []

# DONE encyc.models.legacy
@ring.redis(config.CACHE, coder='json')
def author_articles(title: str) -> List[str]:
    """
    @param title: str
    @returns: list of strs
    """
    w = MediaWiki()
    return [page.name for page in w.mw.Pages.get(title).backlinks()]

@ring.redis(config.CACHE, coder='json')
def category_members(category_name: str, namespace_id: str=None) -> List[Dict[str,str]]:
    """Returns titles of pages with specified Category: tag.
    
    NOTE: Rather than just returning a list of title strings, this returns
    a list of _dicts_ containing namespace id, title, and sortkey.
    This is so certain views (e.g. Contents A-Z can grab the first letter
    of the title (or sortkey) to use for grouping purposes.
    
    @param category_name: str
    @param namespace_id: str
    @returns: list of encyc.wiki.Page
    """
    w = MediaWiki()
    return [Page(page) for page in w.mw.categories[category_name]]

# DONE encyc.models.legacy
def category_article_types():
    """Returns list of subcategories underneath 'Article'.
    @returns: list of encyc.wiki.Page
    """
    w = MediaWiki()
    return [Page(page) for page in w.mw.categories['Articles']]
def category_authors():
    """
    @returns: list of dicts
    """
    w = MediaWiki()
    return list(w.mw.categories['Authors'])
def category_supplemental():
    """
    @returns: list of dicts
    """
    w = MediaWiki()
    return list(w.mw.categories['Supplemental_Materials'])

# DONE encyc.models.legacy
def is_article(title: str) -> bool:
    """
    @param title: str
    @returns: bool
    """
    return title in [page.name for page in published_pages()]

# DONE encyc.models.legacy
def is_author(title: str) -> bool:
    """
    @param title: str
    @returns: bool
    """
    w = MediaWiki()
    page = w.mw.pages[title]
    return 'Category:Authors' in [cat.name for cat in page.categories()]

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
    
# DONE encyc.models.legacy
#@ring.redis(config.CACHE, coder='json')
def published_pages(cached_ok: bool=True) -> List[Page]:
    """Returns a list of *published* articles (pages), with timestamp of latest revision.
    @param cached_ok: boolean Whether cached results are OK.
    @returns: list of encyc.wiki.Page
    """
    w = MediaWiki()
    authors = [page.name for page in w.mw.categories['Authors']]
    return [
        Page(page) for page in w.mw.categories['Published']
        if not isinstance(page, mwclient.listing.Category)
        and not page.name in authors
    ]

# DONE encyc.models.legacy
#@ring.redis(config.CACHE, coder='json')
def published_authors(cached_ok: bool=True) -> List[Author]:
    """Returns a list of *published* authors (pages), with timestamp of latest revision.
    @param cached_ok: boolean Whether cached results are OK.
    @returns: list of encyc.wiki.Page
    """
    w = MediaWiki()
    published = [
        page.name for page in w.mw.categories['Published']
        if isinstance(page, mwclient.page.Page)
    ]
    authors = []
    for page in [Author(page) for page in w.mw.categories['Authors']]:
        if page.name in published:
            authors.append(page)
    return authors
