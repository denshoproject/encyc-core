from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
from operator import itemgetter
import re
from time import mktime
from typing import List, Set, Dict, Tuple, Optional, Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import mwclient

from encyc import config
from encyc import http

cache = config.CACHE

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

    def articles_a_z(self) -> List[str]:
        """Returns a list of published article titles arranged A-Z.
        @returns: list of encyc.wiki.Page
        """
        key = 'wiki.articles-a-z'
        data = cache.get(key)
        if not data:
            authors = [page.name for page in self.mw.categories['Authors']]
            data = sorted([
                page['title'] for page in self.published_pages()
                if page['title'] not in authors
            ])
            cache.set(key, data, config.CACHE_TIMEOUT)
        return data

    # DONE encyc.models.legacy
    def article_next(self, title: str) -> str:
        """Returns the title of the next article in the A-Z list.
        @param title: str
        @returns: bool
        """
        titles = self.articles_a_z()
        try:
            return titles[titles.index(title) + 1]
        except:
            pass
        return ''

    # DONE encyc.models.legacy
    def article_prev(self, title: str) -> str:
        """Returns the title of the previous article in the A-Z list.
        @param title: str
        @returns: bool
        """
        titles = self.articles_a_z()
        try:
            return titles[titles.index(title) - 1]
        except:
            pass
        return ''

    # DONE encyc.models.legacy
    def author_articles(self, title: str) -> List[str]:
        """
        @param title: str
        @returns: list of strs
        """
        key = f'wiki.author-articles:{title}'
        data = cache.get(key)
        if not data:
            data = [page.name for page in self.mw.Pages.get(title).backlinks()]
            cache.set(key, data, config.CACHE_TIMEOUT)
        return data

    # DONE encyc.models.legacy
    def category_article_types(self):
        """Returns list of subcategories underneath 'Article'.
        @returns: list of encyc.wiki.Page
        """
        key = f'wiki.category_article_types'
        data = cache.get(key)
        if not data:
            data = [category.name for category in self.mw.categories['Articles']]
            cache.set(key, data, config.CACHE_TIMEOUT)
        return data

    # DONE encyc.models.legacy
    def is_article(self, title: str) -> bool:
        """
        @param title: str
        @returns: bool
        """
        return title in [page['title'] for page in self.published_pages()]

    # DONE encyc.models.legacy
    def is_author(self, title: str) -> bool:
        """
        @param title: str
        @returns: bool
        """
        page = self.mw.pages[title]
        return 'Category:Authors' in [cat.name for cat in page.categories()]

    # DONE encyc.models.legacy
    def published_pages(self, cached_ok: bool=True) -> List[Dict[str,str]]:
        """Returns a list of *published* articles (pages), with timestamp of latest revision.
        @param cached_ok: boolean Whether cached results are OK.
        @returns: list of encyc.wiki.Page
        """
        key = 'wiki.published_pages'
        data = cache.get(key)
        if not data:
            data = [
                {
                    'title': page.name,
                    'timestamp': datetime.fromtimestamp(mktime(page.touched)),
                }
                for page in self.mw.categories['Published']
                if not isinstance(page, mwclient.listing.Category)
            ]
            cache.set(key, data, config.CACHE_TIMEOUT)
        return data

    # DONE encyc.models.legacy
    def published_authors(self, cached_ok: bool=True) -> List[Dict[str,str]]:
        """Returns a list of *published* authors (pages), with timestamp of latest revision.
        @param cached_ok: boolean Whether cached results are OK.
        @returns: list of encyc.wiki.Page
        """
        key = 'wiki.published_authors'
        data = cache.get(key)
        if not data:
            published = [
                page.name for page in self.mw.categories['Published']
                if isinstance(page, mwclient.page.Page)
            ]
            data = [
                {
                    'title': page.name,
                }
                for page in self.mw.categories['Authors']
                if page.name in published
            ]
            cache.set(key, data, config.CACHE_TIMEOUT)
        return data
