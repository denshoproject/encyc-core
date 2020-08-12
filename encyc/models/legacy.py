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
        articles = [
            {'first_letter':page['sortkey'][0].upper(), 'title':page.name}
            for page in wiki.published_pages()
        ]
        return articles

    @staticmethod
    def authors(cached_ok=True, columnize=False):
        authors = [page.name for page in wiki.published_authors(cached_ok=cached_ok)]
        if columnize:
            return helpers.columnizer(authors, 4)
        return authors

    @staticmethod
    def articles_lastmod():
        """List of titles and timestamps for all published pages.
        """
        pages = [
            {
                'title': page.name,
                'lastmod': datetime.strptime(page.timestamp, config.MEDIAWIKI_DATETIME_FORMAT_TZ)
            }
            for page in wiki.published_pages(cached_ok=False)
        ]
        return pages

    @staticmethod
    def page(url_title, request=None, rg_titles=[]):
        """
        @param url_title str: Canonical page URL title
        @param request HttpRequest: [optional] Django request object
        @param rg_titles list: Resource Guide url_titles (used to mark links)
        """
        url = helpers.page_data_url(config.MEDIAWIKI_API, url_title)
        logger.debug(url)
        status_code,text = Proxy._mw_page_text(url)
        return Proxy._mkpage(
            url_title,
            status_code,
            text,
            request,
            rg_titles,
        )
    
    @staticmethod
    def _mw_page_text(url_title):
        """
        @param page: Page title from URL.
        """
        logger.debug(url_title)
        url_title = url_title
        page = Page()
        page.url_title = url_title
        page.uri = urls.reverse('wikiprox-page', args=[url_title])
        page.url = helpers.page_data_url(config.MEDIAWIKI_API, page.url_title)
        logger.debug(page.url)
        r = http.get(page.url)
        logger.debug(r.status_code)
        return r.status_code,str(r.text)
    
    @staticmethod
    def _mkpage(url_title, http_status, rawtext, request=None, rg_titles=[]):
        """
        TODO rename me
        @param url_title str: Canonical page URL title
        @param http_status int: 
        @param rawtext str: Body of HTTP request
        @param request HttpRequest: [optional] Django request object
        @param rg_titles list: Resource Guide url_titles (used to mark links)
        """
        logger.debug(url_title)
        url_title = url_title
        page = Page()
        page.url_title = url_title
        page.uri = urls.reverse('wikiprox-page', args=[url_title])
        page.url = helpers.page_data_url(config.MEDIAWIKI_API, page.url_title)
        page.status_code = http_status
        pagedata = json.loads(rawtext)
        page.error = pagedata.get('error', None)
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
            
            # rewrite media URLs on stage
            # (external URLs not visible to Chrome on Android when connecting through SonicWall)
            if hasattr(config, 'STAGE') and config.STAGE and request:
                page.sources = sources.replace_source_urls(page.sources, request)
            
            page.is_article = wiki.is_article(page.title)
            if page.is_article:
                page.description = wikipage.extract_description(page.body)
                
                # only include categories from Category:Articles
                categories_whitelist = [
                    category.name.split(':')[1]
                    for category in wiki.category_article_types()
                ]
                page.categories = [
                    c['*']
                    for c in pagedata['parse']['categories']
                    if c['*'] in categories_whitelist
                ]
                
                page.prev_page = wiki.article_prev(page.title)
                page.next_page = wiki.article_next(page.title)
                page.coordinates = helpers.find_databoxcamps_coordinates(pagedata['parse']['text']['*'])
                page.authors = helpers.find_author_info(pagedata['parse']['text']['*'])
            
            page.is_author = wiki.is_author(page.title)
            if page.is_author:
                page.author_articles = wiki.author_articles(page.title)
            
        return page
    
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


class Elasticsearch(object):
    """Interface to Elasticsearch backend
    
    NOTE: not a Django model object!
    """

    def categories(self):
        s = Search(
            using=docstore.Docstore(),
            doc_type='articles'
        ).fields([
            'title', 'title_sort', 'categories',
        ])[0:docstore.MAX_SIZE]
        if not config.MEDIAWIKI_SHOW_UNPUBLISHED:
            s = s.query('match', published=True)
        response = s.execute()
        pages = []
        for hit in response:
            page = Page()
            page.url_title = hit.title[0]
            page.title = hit.title[0]
            page.title_sort = hit.title_sort[0]
            page.categories = hit.get('categories', [])
            pages.append(page)
        articles = sorted(pages, key=lambda page: page.title_sort)
        categories = {}
        for page in articles:
            for category in page.categories:
                # exclude internal editorial categories
                if category not in config.MEDIAWIKI_HIDDEN_CATEGORIES:
                    if category not in categories.keys():
                        categories[category] = []
                    # pages already sorted so category lists will be sorted
                    if page not in categories[category]:
                        categories[category].append(page)
        return categories
    
    def articles(self):
        s = Search(
            using=docstore.Docstore(),
            doc_type='articles'
        ).fields([
            'title', 'title_sort', 'lastmod',
        ])[0:docstore.MAX_SIZE]
        response = s.execute()
        pages = []
        for hit in response:
            page = Page()
            page.url_title = hit.title[0]
            page.title = hit.title[0]
            page.title_sort = hit.title_sort[0]
            page.first_letter = page.title_sort[0]
            page.lastmod = datetime.strptime(hit.lastmod[0], config.MEDIAWIKI_DATETIME_FORMAT)
            pages.append(page)
        return sorted(pages, key=lambda page: page.title_sort)

    def authors(self, num_columns=0):
        """
        @param num_columns: int If non-zero, break up list into columns
        """
        s = Search(
            using=docstore.Docstore(),
            doc_type='authors'
        ).fields([
            'url_title', 'title', 'title_sort', 'lastmod'
        ])[0:docstore.MAX_SIZE]
        response = s.execute()
        authors = []
        for hit in response:
            url_title = hit.url_title[0]
            title = hit.title[0]
            title_sort = hit.title_sort[0]
            lastmod = hit.lastmod[0]
            if title and title_sort:
                author = Author()
                author.url_title = url_title
                author.title = title
                author.title_sort = title_sort
                author.lastmod = datetime.strptime(lastmod, config.MEDIAWIKI_DATETIME_FORMAT)
                authors.append(author)
        authors = sorted(authors, key=lambda a: a.title_sort)
        if num_columns:
            return helpers.columnizer(authors, num_columns)
        return authors

    def author(self, url_title):
        results = docstore.get(model='authors', document_id=url_title)
        author = Author()
        for key,val in results['_source'].items():
            setattr(author, key, val)
        return author

    def page(self, url_title):
        results = docstore.get(model='articles',document_id=url_title)
        if not results:
            return None
        page = Page()
        for key,val in results['_source'].items():
            setattr(page, key, val)
        # remove page elements for internal editorial use only
        categories = [
            category
            for category in page.categories
            if category not in config.MEDIAWIKI_HIDDEN_CATEGORIES
        ]
        page.categories = categories
        # sources
        #sources = []
        #results = docstore.mget('sources', page.sources)
        #for doc in results['docs']:
        #    source = Source()
        #    for key,val in doc['_source'].items():
        #        setattr(source, key, val)
        #    sources.append(source)
        #page.sources = sources
        return page
    
    def topics(self):
        terms = []
        results = docstore.get(model='vocab', document_id='topics')
        if results['_source']['terms']:
            terms = [
                {
                    'id': term['id'],
                    'title': term['title'],
                    '_title': term['_title'],
                    'encyc_urls': term['encyc_urls'],
                }
                for term in results['_source']['terms']
            ]
        return terms

    def topics_by_url(self):
        terms = {}
        for term in self.topics():
            for url in term['encyc_urls']:
                if not terms.get(url, None):
                    terms[url] = []
                terms[url].append(term)
        return terms

    def related_ddr(self, term_ids, balanced=False):
        """Get objects for terms from DDR.
        Ironic: this uses DDR's REST UI rather than ES.
        """
        return ddr.related_by_topic(
            term_ids=term_ids,
            size=5,
            balanced=balanced
        )
    
    def source(self, encyclopedia_id):
        results = docstore.get(model='sources', document_id=encyclopedia_id)
        source = Source()
        for key,val in results['_source'].items():
            setattr(source, key, val)
        return source

    def citation(self, page):
        return Citation(page)
    
    def index_articles(self, titles=[], start=0, num=1000000):
        """
        @param titles: list of url_titles to retrieve.
        @param start: int Index of list at which to start.
        @param num: int Number of articles to index, beginning at start.
        @returns: (int num posted, list Articles that could not be posted)
        """
        posted = 0
        could_not_post = []
        for n,title in enumerate(titles):
            if (posted < num) and (n > start):
                logging.debug('%s/%s %s' % (n, len(titles), title))
                page = Proxy.page(title)
                if (page.published or config.MEDIAWIKI_SHOW_UNPUBLISHED):
                    page_sources = [source['encyclopedia_id'] for source in page.sources]
                    for source in page.sources:
                        logging.debug('     %s' % source['encyclopedia_id'])
                        docstore.post(source)
                    page.sources = page_sources
                    docstore.post(page)
                    posted = posted + 1
                    logging.debug('posted %s' % posted)
                else:
                    could_not_post.append(page)
        if could_not_post:
            logging.debug('Could not post these: %s' % could_not_post)
        return posted,could_not_post
        
    def index_authors(self, titles=[]):
        """
        @param titles: list of url_titles to retrieve.
        """
        for n,title in enumerate(titles):
            logging.debug('%s/%s %s' % (n, len(titles), title))
            page = Proxy.page(title)
            docstore.post(page)
    
    def delete_articles(self, titles):
        results = []
        for title in titles:
            r = docstore.delete(
                config.DOCSTORE_HOST, 'articles',
                title
            )
            results.append(r)
        return results
    
    def delete_authors(self, titles):
        results = []
        for title in titles:
            r = docstore.delete(
                config.DOCSTORE_HOST, 'authors',
                title
            )
            results.append(r)
        return results

    def index_topics(self, json_text=None, url=config.DDR_TOPICS_SRC_URL):
        """Upload topics.json; used for Encyc->DDR links on article pages.
        
        url = 'http://partner.densho.org/vocab/api/0.2/topics.json'
        models.Elasticsearch().index_topics(url)
        
        @param json_text: unicode Raw topics.json file text.
        @param url: URL of topics.json
        """
        if url and not json_text:
            r = http.get(url)
            if r.status_code == 200:
                json_text = r.text
        docstore.post(json.loads(json_text))
    
    def articles_to_update(self, mw_authors, mw_articles, es_authors, es_articles):
        """Returns titles of articles to update and delete
        
        >>> mw_authors = Proxy.authors(cached_ok=False)
        >>> mw_articles = Proxy.articles_lastmod()
        >>> es_authors = Elasticsearch().authors()
        >>> es_articles = Elasticsearch().articles()
        >>> results = Elasticsearch().articles_to_update(mw_authors, mw_articles, es_authors, es_articles)
        >>> Elasticsearch().index_articles(titles=results['update'])
        >>> Elasticsearch().delete_articles(titles=results['delete'])
        
        @param mw_authors: list Output of wikiprox.models.Proxy.authors_lastmod()
        @param mw_articles: list Output of wikiprox.models.Proxy.articles_lastmod()
        @param es_authors: list Output of wikiprox.models.Elasticsearch.authors()
        @param es_articles: list Output of wikiprox.models.Elasticsearch.articles()
        @returns: dict {'update':..., 'delete':...}
        """
        # filter out the authors
        mw_lastmods = [
            a for a in mw_articles
            if a['title'] not in mw_authors
        ]
        es_pages = [a for a in es_articles if a.title not in es_authors]
        
        mw_titles = [a['title'] for a in mw_lastmods]
        es_titles = [a.title for a in es_pages]
        
        new = [mwtitle for mwtitle in mw_titles if not mwtitle in es_titles]
        deleted = [estitle for estitle in es_titles if not estitle in mw_titles]
        
        mw = {}  # so we don't loop on every es_article
        for a in mw:
            mw[a['title']] = a['lastmod']
        updated = [
            a for a in es_articles
            if (a.title in mw.keys()) and (mw[a.title] > a.lastmod)
        ]
        return {
            'update': new + updated,
            'delete': deleted,
        }
    
    def authors_to_update(self, mw_authors, es_authors):
        """Returns titles of authors to add or delete
        
        Does not track updates because it's easy just to update them all.
        
        >>> mw_authors = Proxy.authors(cached_ok=False)
        >>> es_authors = Elasticsearch().authors()
        >>> results = Elasticsearch().articles_to_update(mw_authors, es_authors)
        >>> Elasticsearch().index_authors(titles=results['update'])
        >>> Elasticsearch().delete_authors(titles=results['delete'])
        
        @param mw_authors: list Output of wikiprox.models.Proxy.authors_lastmod()
        @param es_authors: list Output of wikiprox.models.Elasticsearch.authors()
        @returns: dict {'new':..., 'delete':...}
        """
        es_author_titles = [a.title for a in es_authors]
        new = [title for title in mw_authors if title not in es_author_titles]
        delete = [title for title in es_author_titles if title not in mw_authors]
        return {
            'new': new,
            'delete': delete,
        }

    def update_all(self):
        """Check with Proxy source and update authors and articles.
        
        IMPORTANT: Will lock if unable to connect to MediaWiki server!
        """
        # authors
        mw_authors = Proxy.authors(cached_ok=False)
        es_authors = self.authors()
        results = self.authors_to_update(mw_authors, es_authors)
        self.index_authors(titles=results['new'])
        self.delete_authors(titles=results['delete'])
        # articles
        # authors need to be refreshed
        mw_authors = Proxy.authors(cached_ok=False)
        mw_articles = Proxy.articles_lastmod()
        es_authors = self.authors()
        es_articles = self.articles()
        results = self.articles_to_update(mw_authors, mw_articles, es_authors, es_articles)
        self.delete_articles(titles=results['delete'])
        self.index_articles(titles=results['update'])
