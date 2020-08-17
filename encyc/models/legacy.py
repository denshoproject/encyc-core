import codecs
from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
import re
from typing import List, Set, Dict, Tuple, Optional

from dateutil import parser
from elasticsearch_dsl import Search

from encyc import config
from encyc import csvfile
from encyc import ddr
from encyc import docstore
from encyc import http
from encyc import urls
from encyc import wiki
from encyc.models import citations
from encyc.models import sources
from encyc.models import helpers
from encyc.models import wikipage

STOP_WORDS = ['a', 'an', 'the']

def make_titlesort(title_sort, title):
    """make title_sort from title if necessary; normalize title_sort
    """
    if title_sort:
        text = title_sort
    else:
        # no title_sort, use title and rm initial stop word
        text = title
        first_word = text.split(' ')[0]
        if first_word in STOP_WORDS:
            text = text.replace('%s ' % first_word, '', 1)
    # rm spaces and punctuation, make lowercase
    return ''.join([c for c in text.lower() if c.isalnum()])


# ----------------------------------------------------------------------

class Author(object):
    url_title = None
    uri = None
    title = None
    title_sort = None
    body = None
    lastmod = None
    author_articles = List[str]
    
    def __repr__(self):
        return '<%s.%s "%s">' % (
            self.__module__,
            self.__class__.__name__,
            self.title
        )
    
    def __str__(self):
        return self.title

    def absolute_url(self):
        return urls.reverse('wikiprox-author', args=([self.title]))


class Page(object):
    """Represents a MediaWiki page.
    IMPORTANT: not a Django model object!
    """
    url_title = None
    url = None
    uri = None
    status_code = None
    error = None
    public = None
    published = None
    published_encyc = None
    published_rg = None
    lastmod = None
    is_article = None
    is_author = None
    title_sort = None
    title = None
    description = None
    body = None
    authors = List[str]
    sources = List[str]
    categories = List[str]
    author_articles = List[str]
    coordinates = ()
    prev_page = None
    next_page = None
    databoxes = Dict[str,str]
    
    def __repr__(self):
        return '<%s.%s "%s">' % (
            self.__module__,
            self.__class__.__name__,
            self.url_title
        )
    
    def __str__(self):
        return self.url_title
    
    def absolute_url(self):
        return urls.reverse('wikiprox-page', args=([self.title]))
    
    @staticmethod
    def pagedata(mw: wiki.MediaWiki, url_title: str) -> str:
        url = helpers.page_data_url(config.MEDIAWIKI_API, url_title)
        r = http.get(url)
        return str(r.text)
    
    @staticmethod
    def get(mw: wiki.MediaWiki,
            url_title: str,
            rawtext: str='',
            rg_titles: List[str]=[]
    ):
        """Get page data from API and return Page object.
        """
        logger.debug(url_title)
        page = Page()
        page.url_title = url_title
        page.uri = urls.reverse('wikiprox-page', args=[url_title])
        if rawtext:
            pagedata = json.loads(rawtext)
        else:
            pagedata = json.loads(Page.pagedata(mw, url_title))
        if pagedata.get('error') and pagedata['error']['code'] == 'missingtitle':
            page.status_code = 404
            page.error = pagedata['error']['code']
        else:
            page.status_code = 200
            page.error = None
        if (page.status_code == 200) and not page.error:
            
            page.public = False
            ## hide unpublished pages on public systems
            #page.public = request.META.get('HTTP_X_FORWARDED_FOR',False)
            # note: header is added by Nginx, should not appear when connected directly
            # to the app server.
            page.published = helpers.page_is_published(pagedata)
            page.lastmod = helpers.page_lastmod(config.MEDIAWIKI_API, page.url_title)
            
            # basic page context
            page.title = pagedata['parse']['displaytitle']
            
            title_sort = ''
            for prop in pagedata['parse']['properties']:
                if prop.get('name',None) and prop['name'] \
                and (prop['name'].lower() == 'defaultsort'):
                    title_sort = prop['*']
            page.title_sort = make_titlesort(title_sort, page.title)
            
            page.sources = helpers.find_primary_sources(
                config.SOURCES_API,
                pagedata['parse']['images']
            )
            page.databoxes = wikipage.extract_databoxes(
                pagedata['parse']['text']['*'],
                config.MEDIAWIKI_DATABOXES
            )
            
            page.published_encyc = True
            if wikipage.not_published_encyc(pagedata['parse']['text']['*']):
                # Must be called before marker divs are removed
                # in wikipage._remove_nonrg_divs
                page.published_encyc = False
            
            page.published_rg = False
            if hasattr(page, 'databoxes') and page.databoxes \
            and page.databoxes.get('rgdatabox-Core',{}).get('rgmediatype'):
                page.published_rg = True
            
            page.body = wikipage.parse_mediawiki_text(
                title=url_title,
                html=pagedata['parse']['text']['*'],
                primary_sources=page.sources,
                public=page.public,
                printed=False,
                rg_titles=rg_titles,
            )
            
            ## rewrite media URLs on stage
            ## (external URLs not visible to Chrome on Android when connecting through SonicWall)
            #if hasattr(config, 'STAGE') and config.STAGE and request:
            #    page.sources = sources.replace_source_urls(page.sources, request)
            
            page.is_article = mw.is_article(page.title)
            if page.is_article:
                page.description = wikipage.extract_description(page.body)
                
                # only include categories from Category:Articles
                categories_whitelist = [
                    category.split(':')[1]
                    for category in mw.category_article_types()
                ]
                page.categories = [
                    c['*']
                    for c in pagedata['parse']['categories']
                    if c['*'] in categories_whitelist
                ]
                
                page.prev_page = mw.article_prev(page.title)
                page.next_page = mw.article_next(page.title)
                page.coordinates = helpers.find_databoxcamps_coordinates(pagedata['parse']['text']['*'])
                page.authors = helpers.find_author_info(pagedata['parse']['text']['*'])
            
            page.is_author = mw.is_author(page.title)
            if page.is_author:
                page.author_articles = mw.author_articles(page.title)
            
        return page
    
    def topics(self):
        terms = Elasticsearch().topics_by_url().get(self.absolute_url(), [])
        for term in terms:
            term['ddr_topic_url'] = '%s/%s/' % (
                config.DDR_TOPICS_BASE, term['id'])
        return terms


SOURCE_FIELDS = [
    'id', 'encyclopedia_id', 'densho_id', 'resource_uri', 'institution_id',
    'collection_name', 'created', 'modified', 'published', 'creative_commons',
    'headword',
    'original', 'original_size', 'original_url', 'original_path',
    'original_path_abs',
    'display', 'display_size', 'display_url', 'display_path', 'display_path_abs',
    'external_url', 'media_format', 'aspect_ratio',
    'caption', 'caption_extended', 'transcript', 'courtesy',
]

class Source(object):
    
    def __init__(self, *args, **kwargs):
        self.rtmp_streamer = config.RTMP_STREAMER
        self.authors = {'display':[], 'parsed':[],}
        for field in SOURCE_FIELDS:
            setattr(self, field, '')
    
    def __repr__(self):
        return '<%s.%s "%s">' % (
            self.__module__,
            self.__class__.__name__,
            self.encyclopedia_id
        )
    
    def absolute_url(self):
        return urls.reverse('wikiprox-source', args=([self.encyclopedia_id]))
    
    @staticmethod
    def source(data):
        encyclopedia_id = data['encyclopedia_id']
        source = Source()
        source.encyclopedia_id = encyclopedia_id
        source.uri = urls.reverse('wikiprox-source', args=[encyclopedia_id])
        source.title = encyclopedia_id
        for key,val in data.items():
            setattr(source, key, val)
        source.psms_id = int(data['id'])
        if data.get('original_size'):
            source.original_size = int(data['original_size'])
        source.created = parser.parse(data['created'])
        source.modified = parser.parse(data['modified'])
        if getattr(source, 'streaming_url', None):
            source.streaming_url = source.streaming_url.replace(
                config.RTMP_STREAMER,''
            )
            source.rtmp_streamer = config.RTMP_STREAMER
        source.original_url = source.original
        if source.original:
            source.original = os.path.basename(source.original)
            source.original_path = source.original_url.replace(
                config.SOURCES_URL, ''
            )
            source.original_path_abs = os.path.join(
                config.SOURCES_BASE, source.original_path
            )
            # just in case we end up with sources/sources
            source.original_path_abs = source.original_path_abs.replace(
                'sources/sources', 'sources')
        source.display_url = source.display
        if source.display:
            source.display = os.path.basename(source.display)
            source.display_path = source.display_url.replace(
                config.SOURCES_URL, ''
            )
            source.display_path_abs = os.path.join(
                config.SOURCES_BASE, source.display_path
            )
            # just in case we end up with sources/sources
            source.display_path_abs = source.display_path_abs.replace(
                'sources/sources', 'sources')
        source.external_url = fix_external_url(source.external_url)
        return source

EXTERNAL_URL_PATTERN = re.compile('http://ddr.densho.org/(\w+)/(\w+)/(\d+)/(\d+)/')
EXTERNAL_URL_REPLACEMENT = r'http://ddr.densho.org/\1-\2-\3-\4/'

def fix_external_url(url):
    """Update Source.external_urls in legacy DDR format
    
    http://lccn.loc.gov/sn83025333          -> NOOP
    http://ddr.densho.org/ddr-densho-67-19/ -> NOOP
    http://ddr.densho.org/ddr/densho/67/19/ -> http://ddr.densho.org/ddr-densho-67-19/
    """
    m = re.match(EXTERNAL_URL_PATTERN, url)
    if m:
        return re.sub(EXTERNAL_URL_PATTERN, EXTERNAL_URL_REPLACEMENT, url)
    return url


class Citation(object):
    """Represents a citation for a MediaWiki page.
    IMPORTANT: not a Django model object!
    """
    url_title = None
    url = None
    page_url = None
    cite_url = None
    href = None
    status_code = None
    error = None
    title = None
    lastmod = None
    retrieved = None
    authors = List[str]
    authors_apa = ''
    authors_bibtex = ''
    authors_chicago = ''
    authors_cse = ''
    authors_mhra = ''
    authors_mla = ''
    
    def __repr__(self):
        return "<Citation '%s'>" % self.url_title
    
    def __str__(self):
        return self.url_title
    
    def __init__(self, page):
        self.uri = page.uri
        self.title = page.title
        if getattr(page, 'lastmod', None):
            self.lastmod = page.lastmod
        elif getattr(page, 'modified', None):
            self.lastmod = page.modified
        self.retrieved = datetime.now()
        self.authors = page.authors
        self.authors_apa = citations.format_authors_apa(self.authors['parsed'])
        self.authors_bibtex = citations.format_authors_bibtex(self.authors['parsed'])
        self.authors_chicago = citations.format_authors_chicago(self.authors['parsed'])
        self.authors_cse = citations.format_authors_cse(self.authors['parsed'])
        self.authors_mhra = citations.format_authors_mhra(self.authors['parsed'])
        self.authors_mla = citations.format_authors_mla(self.authors['parsed'])


class Proxy(object):
    """Interface to back-end MediaWiki site and encyc-psms
    
    NOTE: not a Django model object!
    """

    @staticmethod
    def articles():
        mw = wiki.MediaWiki()
        articles = [
            {'first_letter':page['sortkey'][0].upper(), 'title':page.name}
            for page in mw.published_pages()
        ]
        return articles

    @staticmethod
    def authors(mw, cached_ok=True, columnize=False):
        authors = [author['title'] for author in mw.published_authors()]
        if columnize:
            return helpers.columnizer(authors, 4)
        return authors

    @staticmethod
    def articles_lastmod(mw):
        """List of titles and timestamps for all published pages.
        """
        pages = [
            {
                'title': page['title'],
                'lastmod': page['timestamp'],
            }
            for page in mw.published_pages(cached_ok=False)
        ]
        return pages
    
    @staticmethod
    def sources_all():
        """Get all published sources from SOURCES_API.
        """
        URL = config.SOURCES_API + '/sources/'
        r = http.get(URL, headers={'content-type':'application/json'})
        if r.status_code != 200:
            return []
        return [Source.source(data) for data in json.loads(r.text)]

    @staticmethod
    def citation(page):
        return Citation(page)



class Contents:
    
    def __init__(self):
        results = docstore.search(
            doctypes=['articles'],
            fields=['title', 'title_sort',],
        )
        self._articles = []
        for hit in results['hits']['hits']:
            page = Page()
            page.url_title = hit['fields']['title'][0]
            page.title = hit['fields']['title'][0]
            page.title_sort = hit['fields']['title_sort'][0]
            page.first_letter = page.title_sort[0]
            self._articles.append(page)
    
    def __len__(self):
        return len(self._articles)

    def __getitem__(self, position):
        return self._articles[position]
