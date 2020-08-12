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

# DONE encyc.models.legacy
def category_article_types():
    """Returns list of subcategories underneath 'Article'.
    @returns: list of encyc.wiki.Page
    """
    w = MediaWiki()
    return [Page(page) for page in w.mw.categories['Articles']]

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
