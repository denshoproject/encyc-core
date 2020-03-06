"""Encyclopedia models using Elasticsearch-DSL


TODO "Article(s)" is often used to mean "Page(s)".


See wikiprox/management/commands/encycpudate.py

# Delete and recreate index
$ python manage.py encycupdate --reset

# Update authors
$ python manage.py encycupdate --authors

# Update articles
$ python manage.py encycupdate --articles

Example usage:

>>> from encyc import config
>>> from encyc.models import Elasticsearch, Author, Page, Source
>>> authors = [author for author in Author.authors()]
>>> pages = [page for page in Page.pages()]
>>> sources = [source for source in Source.search().execute()]
"""

from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
from urllib.parse import unquote, urlparse

from dateutil import parser
import requests

from elasticsearch.exceptions import NotFoundError
import elasticsearch_dsl as dsl

from encyc import config
from encyc import ddr
from encyc import docstore
from encyc import http
from encyc.models import citations
from encyc.models.legacy import Proxy
from encyc import repo_models
from encyc import search
from encyc import urls

if not config.DEBUG:
    from bs4 import BeautifulSoup
    from encyc.models.wikipage import remove_status_markers

MAX_SIZE = 10000


def _columnizer(things, cols):
    columns = []
    collen = round(len(things) / float(cols))
    col = []
    for t in things:
        col.append(t)
        if len(col) > collen:
           columns.append(col)
           col = []
    columns.append(col)
    return columns

def hitvalue(hit, field):
    """
    For some reason, Search hit objects wrap values in lists.
    returns the value inside the list.
    """
    v = getattr(hit,field)
    if v and isinstance(v, list):
        value = v[0]
    else:
        value = v
    return value

def none_strip(text):
    """Turn Nones into empty str, strip whitespace.
    """
    if text == None:
        text = ''
    return text.strip()


class Author(repo_models.Author):

    @staticmethod
    def get(title):
        ds = docstore.Docstore()
        return super(Author, Author).get(
            title, index=ds.index_name('author'), using=ds.es
    )
    
    def save(self):
        ds = docstore.Docstore()
        return super(Author, self).save(index=ds.index_name('author'), using=ds.es)
    
    def delete(self):
        ds = docstore.Docstore()
        return super(Author, self).delete(index=ds.index_name('author'), using=ds.es)

    def absolute_url(self):
        return urls.reverse('wikiprox-author', args=([self.title,]))
    
    def articles(self):
        """Returns list of published light Pages for this Author.
        
        @returns: list
        """
        return [
            page
            for page in Page.pages()
            if page.url_title in self.article_titles
        ]

    @staticmethod
    def authors(num_columns=None):
        """Returns list of published light Author objects.
        
        @returns: list
        """
        searcher = search.Searcher()
        searcher.prepare(
            params={},
            search_models=[docstore.Docstore().index_name('author')],
            fields_nested=[],
            fields_agg={},
        )
        return searcher.execute(docstore.MAX_SIZE, 0)

    def scrub(self):
        """Removes internal editorial markers.
        Must be run on a full (non-list) Page object.
        TODO Should this happen upon import from MediaWiki?
        """
        if (not config.DEBUG) and hasattr(self,'body') and self.body:
            self.body = unicode(remove_status_markers(BeautifulSoup(self.body)))

    @staticmethod
    def from_mw(mwauthor, author=None):
        """Creates an Author object from a models.legacy.Author object.
        """
        if author:
            author.public = mwauthor.public
            author.published = mwauthor.published
            author.modified = mwauthor.lastmod
            author.mw_api_url = mwauthor.uri
            author.title_sort = mwauthor.title_sort
            author.title = none_strip(mwauthor.title)
            author.body = none_strip(mwauthor.body)
            author.article_titles = [title for title in mwauthor.author_articles]
        else:
            author = Author(
                meta = {'id': mwauthor.url_title},
                #status_code = myauthor.status_code,
                #error = myauthor.error,
                #is_article = myauthor.is_article,
                #is_author = myauthor.is_author,
                #uri = mwauthor.uri,
                #categories = myauthor.categories,
                #sources = myauthor.sources,
                #coordinates = myauthor.coordinates,
                #authors = myauthor.authors,
                #next_path = myauthor.next_path,
                #prev_page = myauthor.prev_page,
                url_title = mwauthor.url_title,
                public = mwauthor.public,
                published = mwauthor.published,
                modified = mwauthor.lastmod,
                mw_api_url = mwauthor.uri,
                title_sort = mwauthor.title_sort,
                title = none_strip(mwauthor.title),
                body = none_strip(mwauthor.body),
                article_titles = [title for title in mwauthor.author_articles],
            )
        return author


class Page(repo_models.Page):

    @staticmethod
    def get(title):
        ds = docstore.Docstore()
        return super(Page, Page).get(
            id=title, index=ds.index_name('article'), using=ds.es
        )
    
    def save(self):
        ds = docstore.Docstore()
        return super(Page, self).save(index=ds.index_name('article'), using=ds.es)
    
    def delete(self):
        ds = docstore.Docstore()
        return super(Page, self).delete(index=ds.index_name('article'), using=ds.es)
    
    def absolute_url(self):
        return urls.reverse('wikiprox-page', args=([self.title]))

    def authors(self):
        """Returns list of published light Author objects for this Page.
        
        @returns: list
        """
        objects = []
        for url_title in self.authors_data['display']:
            try:
                author = Author.get(url_title)
            except NotFoundError:
                author = url_title
            objects.append(author)
        return objects

    def first_letter(self):
        return self.title_sort[0]
    
    @staticmethod
    def pages():
        """Returns list of published light Page objects.
        
        @returns: list
        """
        searcher = search.Searcher()
        searcher.prepare(
            params={},
            search_models=[docstore.Docstore().index_name('article')],
            fields_nested=[],
            fields_agg={},
        )
        return searcher.execute(docstore.MAX_SIZE, 0)
    
    @staticmethod
    def pages_by_category():
        """Returns list of (category, Pages) tuples, alphabetical by category
        
        @returns: list
        """
        categories = {}
        for page in Page.pages():
            for category in page.categories:
                # exclude internal editorial categories
                if category not in config.MEDIAWIKI_HIDDEN_CATEGORIES:
                    if category not in categories.keys():
                        categories[category] = []
                    # pages already sorted so category lists will be sorted
                    if page not in categories[category]:
                        categories[category].append(page)
        data = [
            (key,categories[key])
            for key in sorted(categories.keys())
        ]
        return data

    def scrub(self):
        """remove internal editorial markers.
        
        Must be run on a full (non-list) Page object.
        TODO Should this happen upon import from MediaWiki?
        """
        if (not config.DEBUG) and hasattr(self,'body') and self.body:
            self.body = unicode(remove_status_markers(BeautifulSoup(self.body)))
    
    def sources(self):
        """Returns list of published light Source objects for this Page.
        
        @returns: list
        """
        return [Source.get(sid) for sid in self.source_ids]
    
    def topics(self):
        """List of DDR topics associated with this page.
        
        @returns: list
        """
        # return list of dicts rather than an Elasticsearch results object
        terms = []
        for t in Elasticsearch.topics_by_url().get(self.absolute_url(), []):
            term = {
                key: val
                for key,val in t.iteritems()
            }
            term.pop('encyc_urls')
            term['ddr_topic_url'] = '%s/%s/' % (
                config.DDR_TOPICS_BASE,
                term['id']
            )
            terms.append(term)
        return terms
    
    def ddr_terms_objects(self, size=100):
        """Get dict of DDR objects for article's DDR topic terms.
        
        Ironic: this uses DDR's REST UI rather than ES.
        """
        if not hasattr(self, '_related_terms_docs'):
            terms = self.topics()
            objects = ddr.related_by_topic(
                term_ids=[term['id'] for term in terms],
                size=size
            )
            for term in terms:
                term['objects'] = objects[term['id']]
        return terms
    
    def ddr_objects(self, size=5):
        """Get list of objects for terms from DDR.
        
        Ironic: this uses DDR's REST UI rather than ES.
        """
        objects = ddr.related_by_topic(
            term_ids=[term['id'] for term in self.topics()],
            size=size
        )
        return ddr._balance(objects, size)
    
    @staticmethod
    def rg_titles():
        """List of articles appearing in the Resource Guide (encycrg)
        """
        url = os.path.join(config.ENCYCRG_API, 'articles')
        try:
            r = requests.get(url)
            logging.debug(r.status_code)
            articles = json.loads(r.text)['objects']
        except:
            logging.debug('ERROR')
            articles = []
        return [a['id'] for a in articles]

    @staticmethod
    def from_mw(mwpage, page=None):
        """Creates an Page object from a models.legacy.Page object.
        """
        try:
            authors = mwpage.authors
        except AttributeError:
            authors = []
        if page:
            page.public = mwpage.public
            page.published = mwpage.published
            page.published_encyc = mwpage.published_encyc
            page.published_rg = mwpage.published_rg
            page.modified = mwpage.lastmod
            page.mw_api_url = mwpage.url
            page.title_sort = mwpage.title_sort
            page.title = none_strip(mwpage.title)
            page.description = mwpage.description
            page.body = none_strip(mwpage.body)
            page.prev_page = mwpage.prev_page
            page.next_page = mwpage.next_page
            page.categories = [category for category in mwpage.categories]
            page.coordinates = [coord for coord in mwpage.coordinates]
            page.source_ids = [source['encyclopedia_id'] for source in mwpage.sources]
            page.authors_data = authors
        else:
            page = Page(
                meta = {'id': mwpage.url_title},
                #status_code = mwpage.status_code,
                #error = mwpage.error,
                #is_article = mwpage.is_article,
                #is_author = mwpage.is_author,
                #uri = mwpage.uri,
                url_title = mwpage.url_title,
                public = mwpage.public,
                published = mwpage.published,
                published_encyc = mwpage.published_encyc,
                published_rg = mwpage.published_rg,
                modified = mwpage.lastmod,
                mw_api_url = mwpage.url,
                title_sort = mwpage.title_sort,
                title = none_strip(mwpage.title),
                description = mwpage.description,
                body = none_strip(mwpage.body),
                prev_page = mwpage.prev_page,
                next_page = mwpage.next_page,
                categories = [category for category in mwpage.categories],
                coordinates = [coord for coord in mwpage.coordinates],
                source_ids = [source['encyclopedia_id'] for source in mwpage.sources],
                authors_data = authors,
            )
        if mwpage.databoxes:
            # naive implementation: just dump every databox field into Page.
            # Field names are just "PREFIX_" plus lowercased fieldname.
            for key,databox in mwpage.databoxes.iteritems():
                # only include databoxes in configs
                if key in config.MEDIAWIKI_DATABOXES.keys():
                    prefix = config.MEDIAWIKI_DATABOXES.get(key)
                    if prefix:
                        for fieldname,data in databox.iteritems():
                            fieldname = '%s_%s' % (prefix, fieldname)
                            setattr(page, fieldname, data)
            databoxes = [
                '%s|%s' % (key, json.dumps(databox))
                for key,databox in mwpage.databoxes.iteritems()
                # only include databoxes in configs
                if databox and (key in config.MEDIAWIKI_DATABOXES.keys())
            ]
            if databoxes:
                setattr(page, 'databoxes', databoxes)
        
        return page


class Source(repo_models.Source):

    @staticmethod
    def get(title):
        ds = docstore.Docstore()
        return super(Source, Source).get(
            title, index=ds.index_name('source'), using=ds.es
        )
    
    def save(self):
        ds = docstore.Docstore()
        return super(Source, self).save(index=ds.index_name('source'), using=ds.es)
    
    def delete(self):
        ds = docstore.Docstore()
        return super(Source, self).delete(index=ds.index_name('source'), using=ds.es)
    
    def absolute_url(self):
        return urls.reverse('wikiprox-source', args=([self.encyclopedia_id]))
    
    def img_url(self):
        return os.path.join(config.SOURCES_MEDIA_URL, self.img_path)
    
    def img_url_local(self):
        return os.path.join(config.SOURCES_MEDIA_URL_LOCAL, self.img_path)
    
    #def streaming_url(self):
    #    return os.path.join(config.SOURCES_MEDIA_URL, self.streaming_path)
    
    def transcript_url(self):
        if self.transcript_path():
            return os.path.join(config.SOURCES_MEDIA_URL, self.transcript_path())

    def rtmp_path(self):
        return self.streaming_url
    
    def streaming_path(self):
        if self.streaming_url:
            return os.path.join(
                config.SOURCES_MEDIA_BUCKET,
                os.path.basename(self.streaming_url)
            )
        return None
    
    def transcript_path(self):
        if self.transcript:
            return os.path.join(
                config.SOURCES_MEDIA_BUCKET,
                os.path.basename(self.transcript)
            )
        return None
    
    def article(self):
        if self.headword:
            try:
                page = Page.get(self.headword)
            except NotFoundError:
                page = None
        return page
    
    @staticmethod
    def sources():
        """Returns list of published light Source objects.
        
        @returns: list
        """
        searcher = search.Searcher()
        searcher.prepare(
            params={},
            search_models=[docstore.Docstore().index_name('source')],
            fields_nested=[],
            fields_agg={},
        )
        return searcher.execute(docstore.MAX_SIZE, 0)

    @staticmethod
    def from_psms(ps_source):
        """Creates an Source object from a models.legacy.Proxy.source object.
        
        @param ps_source: encyc.models.legacy.Source
        #@param url_title: str url_title of associated Page
        @returns: wikiprox.models.elastic.Source
        """
        # source.streaming_url has to be relative to RTMP_STREAMER
        # TODO this should really happen when it's coming in from MediaWiki.
        if hasattr(ps_source,'streaming_url') and ps_source.streaming_url:
            streaming_url = ps_source.streaming_url.replace(config.RTMP_STREAMER, '')
        else:
            streaming_url = ''
        # fullsize image for thumbnail
        filename = ''
        img_path = ''
        if hasattr(ps_source,'display') and ps_source.display:
            filename = os.path.basename(ps_source.display)
            img_path = os.path.join(config.SOURCES_MEDIA_BUCKET, filename)
        elif hasattr(ps_source,'original') and ps_source.original:
            filename = os.path.basename(ps_source.original)
            img_path = os.path.join(config.SOURCES_MEDIA_BUCKET, filename)
        source = Source(
            meta = {'id': ps_source.encyclopedia_id},
            encyclopedia_id = ps_source.encyclopedia_id,
            densho_id = ps_source.densho_id,
            psms_id = ps_source.id,
            psms_api_uri = ps_source.resource_uri,
            institution_id = ps_source.institution_id,
            collection_name = ps_source.collection_name,
            created = ps_source.created,
            modified = ps_source.modified,
            published = ps_source.published,
            creative_commons = ps_source.creative_commons,
            headword = ps_source.headword,
            
            original = os.path.basename(ps_source.original),
            original_size = ps_source.original_size,
            original_url = ps_source.original_url,
            original_path = ps_source.original_path,
            original_path_abs = ps_source.original_path_abs,
            display = os.path.basename(ps_source.display),
            display_size = ps_source.display_size,
            display_url = ps_source.display_url,
            display_path = ps_source.display_path,
            display_path_abs = ps_source.display_path_abs,
            
            streaming_url = streaming_url,
            external_url = ps_source.external_url,
            media_format = ps_source.media_format,
            aspect_ratio = ps_source.aspect_ratio,
            caption = none_strip(ps_source.caption),
            caption_extended = none_strip(ps_source.caption_extended),
            transcript = none_strip(ps_source.transcript),
            courtesy = none_strip(ps_source.courtesy),
            filename = filename,
            img_path = img_path,
        )
        return source

    @staticmethod
    def from_mw(mwsource, url_title):
        """Creates an Source object from a models.legacy.Source object.
        
        @param mwsource: wikiprox.models.legacy.Source
        @param url_title: str url_title of associated Page
        @returns: wikiprox.models.elastic.Source
        """
        # source.streaming_url has to be relative to RTMP_STREAMER
        # TODO this should really happen when it's coming in from MediaWiki.
        if mwsource.get('streaming_url'):
            streaming_url = mwsource['streaming_url'].replace(config.RTMP_STREAMER, '')
        else:
            streaming_url = ''
        # fullsize image for thumbnail
        filename = ''
        img_path = ''
        if mwsource.get('display'):
            filename = os.path.basename(mwsource['display'])
            img_path = os.path.join(config.SOURCES_MEDIA_BUCKET, filename)
        elif mwsource.get('original'):
            filename = os.path.basename(mwsource['original'])
            img_path = os.path.join(config.SOURCES_MEDIA_BUCKET, filename)
        source = Source(
            meta = {'id': mwsource['encyclopedia_id']},
            encyclopedia_id = mwsource['encyclopedia_id'],
            densho_id = mwsource['densho_id'],
            psms_id = mwsource['id'],
            psms_api_uri = mwsource['resource_uri'],
            institution_id = mwsource['institution_id'],
            collection_name = mwsource['collection_name'],
            created = mwsource['created'],
            modified = mwsource['modified'],
            published = mwsource['published'],
            creative_commons = mwsource['creative_commons'],
            headword = url_title,
            original_url = mwsource['original'],
            streaming_url = streaming_url,
            external_url = mwsource['external_url'],
            media_format = mwsource['media_format'],
            aspect_ratio = mwsource['aspect_ratio'],
            original_size = mwsource['original_size'],
            display_size = mwsource['display_size'],
            display = mwsource['display'],
            caption = none_strip(mwsource['caption']),
            caption_extended = none_strip(mwsource['caption_extended']),
            transcript = none_strip(mwsource['transcript']),
            courtesy = none_strip(mwsource['courtesy']),
            filename = filename,
            img_path = img_path,
        )
        return source


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
    authors = []
    authors_apa = ''
    authors_bibtex = ''
    authors_chicago = ''
    authors_cse = ''
    authors_mhra = ''
    authors_mla = ''
    
    def __repr__(self):
        return "<Citation '%s'>" % self.url_title
    
    def __init__(self, page, request):
        self.uri = page.absolute_url()
        self.href = 'http://%s%s' % (request.META['HTTP_HOST'], self.uri)
        if getattr(page, 'title', None):
            self.title = page.title
        elif getattr(page, 'caption', None):
            self.title = page.caption
        if getattr(page, 'lastmod', None):
            self.lastmod = page.lastmod
        elif getattr(page, 'modified', None):
            self.lastmod = page.modified
        if getattr(page, 'authors_data', None):
            self.authors = page.authors_data
            self.authors_apa = citations.format_authors_apa(self.authors['parsed'])
            self.authors_bibtex = citations.format_authors_bibtex(self.authors['parsed'])
            self.authors_chicago = citations.format_authors_chicago(self.authors['parsed'])
            self.authors_cse = citations.format_authors_cse(self.authors['parsed'])
            self.authors_mhra = citations.format_authors_mhra(self.authors['parsed'])
            self.authors_mla = citations.format_authors_mla(self.authors['parsed'])
        self.retrieved = datetime.now()


class FacetTerm(repo_models.FacetTerm):

    @staticmethod
    def get(title):
        ds = docstore.Docstore()
        return repo_models.FacetTerm.get(
            title, index=ds.index_name('facetterm'), using=ds.es
        )
    
    def save(self):
        ds = docstore.Docstore()
        return super(FacetTerm, self).save(
            index=ds.index_name('facetterm'), using=ds.es)
    
    def delete(self):
        ds = docstore.Docstore()
        return super(FacetTerm, self).delete(
            index=ds.index_name('facetterm'), using=ds.es)
    
    @staticmethod
    def from_dict(facet_id, data):
        oid = '-'.join([
            facet_id, str(data['id'])
        ])
        term = FacetTerm(
            meta = {'id': oid},
            id = oid,
            facet_id = facet_id,
            term_id = data['id'],
            title = data['title'],
        )

        if facet_id in ['topics', 'topic']:
            term._title = data['_title']
            term.description = data['description']
            term.path = data['path']
            term.ancestors = data['ancestors']
            term.children = data['children']
            term.siblings = data['siblings']
            term.encyc_urls = []
            if data.get('encyc_urls'):
                for item in data['encyc_urls']:
                    # just the title part of the URL
                    url = urlparse(item).path.replace('/','')
                    encyc_url = {
                        'url_title': url,
                        'title': unquote(url),
                    }
                    term.encyc_urls.append(encyc_url)
            term.parent_id = None
            if data.get('parent_id'):
                term.parent_id = int(data['parent_id'])
            term.weight = None
            if data.get('weight'):
                term.weight = int(data['weight'])
        
        elif facet_id in ['facilities', 'facility']:
            term.type = data['type']
            term.encyc_urls = []
            if data.get('elinks'):
                for item in data['elinks']:
                    # just the title part of the URL, leave the domain etc
                    encyc_url = {
                        'url_title': urlparse(item['url']).path.replace('/',''),
                        'title': item['label'],
                    }
                    term.encyc_urls.append(encyc_url)
            term.locations = []
            # TODO make this handle multiple locations
            term.locations.append(
                data['location']
            )
        return term

    @staticmethod
    def terms(facet_id=None):
        """Returns list of Terms for facet_id.
        
        @returns: list
        """
        s = FacetTerm.search()[0:MAX_SIZE]
        if facet_id:
            s = s.query("match", facet_id=facet_id)
        s = s.sort('id')
        response = s.execute()
        data = [
            FacetTerm(
                id = hitvalue(hit, 'id'),
                facet_id = hitvalue(hit, 'facet_id'),
                title = hitvalue(hit, 'title'),
                type = hitvalue(hit, 'type'),
            )
            for hit in response
        ]
        return data


class Facet(repo_models.Facet):

    @staticmethod
    def get(title):
        ds = docstore.Docstore()
        return repo_models.Facet.get(
            title, index=ds.index_name('facet'), using=ds.es
        )
    
    def save(self):
        ds = docstore.Docstore()
        return super(Facet, self).save(index=ds.index_name('facet'), using=ds.es)
    
    def delete(self):
        ds = docstore.Docstore()
        return super(Facet, self).delete(index=ds.index_name('facet'), using=ds.es)

    @staticmethod
    def facets():
        """Returns list of Facets.
        
        @returns: list
        """
        s = Facet.search()[0:MAX_SIZE]
        s = s.sort('id')
        response = s.execute()
        data = [
            FacetTerm(
                id = hitvalue(hit, 'id'),
                title = hitvalue(hit, 'title'),
                description = hitvalue(hit, 'description'),
            )
            for hit in response
        ]
        return data
    
    @staticmethod
    def retrieve(facet_id):
        url = '%s/%s.json' % (config.DDR_VOCABS_BASE, facet_id)
        logging.debug(url)
        r = requests.get(url)
        logging.debug(r.status_code)
        data = json.loads(r.text)
        facet = Facet(
            meta = {'id': facet_id},
            id=data['id'],
            title=data['title'],
            description=data['description'],
        )
        facet.terms = [
            FacetTerm.from_dict(facet_id, d)
            for d in data['terms']
        ]
        return facet


class Elasticsearch(object):
    """Interface to Elasticsearch backend
    NOTE: not a Django model object!
    """

    @staticmethod
    def topics():
        terms = []
        results = docstore.get(model='vocab', document_id='topics')
        if results and (results['_source']['terms']):
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

    @staticmethod
    def topics_by_url():
        data = {}
        for term in Elasticsearch.topics():
            for url in term['encyc_urls']:
                if not data.get(url, None):
                    data[url] = []
                data[url].append(term)
        return data
    
    @staticmethod
    def index_articles(titles=[], start=0, num=1000000):
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
                mwpage = Proxy.page(title)
                if (mwpage.published or config.MEDIAWIKI_SHOW_UNPUBLISHED):
                    page_sources = [source['encyclopedia_id'] for source in mwpage.sources]
                    for mwsource in mwpage.sources:
                        logging.debug('     %s' % mwsource['encyclopedia_id'])
                        source = Source.from_mw(mwsource)
                        source.save()
                    page = Page.from_mw(mwpage)
                    page.save()
                    posted = posted + 1
                    logging.debug('posted %s' % posted)
                else:
                    could_not_post.append(page)
        if could_not_post:
            logging.debug('Could not post these: %s' % could_not_post)
        return posted,could_not_post

    @staticmethod
    def index_author(title):
        """
        @param title: str
        """
        for n,title in enumerate(titles):
            logging.debug('%s/%s %s' % (n, len(titles), title))
            mwauthor = Proxy.page(title)
            author = Author.from_mw(mwauthor)
            author.save()

    @staticmethod
    def index_topics(json_text=None, url=config.DDR_TOPICS_SRC_URL):
        """Upload topics.json; used for Encyc->DDR links on article pages.
        
        url = 'http://partner.densho.org/vocab/api/0.2/topics.json'
        models.Elasticsearch.index_topics(url)
        
        @param json_text: unicode Raw topics.json file text.
        @param url: URL of topics.json
        """
        logging.debug('getting topics: %s' % url)
        if url and not json_text:
            r = http.get(url)
            if r.status_code == 200:
                json_text = r.text
                logging.debug('ok')
        docstore.Docstore().post_json('vocab', 'topics', json_text)

    @staticmethod
    def _new_update_deleted(mw_pages, es_objects):
        """
        @param mw_pages: dict MediaWiki articles keyed to titles
        @param es_objects: dict Page or Author objects keyed to titles
        @returns: tuple containing lists of titles (new+updated, deleted)
        """
        def force_dt(val):
            if isinstance(val, datetime):
                return val
            return parser.parse(val)
        new = [
            title for title in mw_pages.keys() if not title in es_objects.keys()
        ]
        deleted = [
            title for title in es_objects.keys() if not title in mw_pages.keys()
        ]
        updated = [
            es.title for es in es_objects.values()
            if mw_pages.get(es.title)
            and (force_dt(mw_pages[es.title]['lastmod']) > force_dt(es.modified))
        ]
        return (new + updated, deleted)
    
    @staticmethod
    def articles_to_update(mw_author_titles, mw_articles, es_articles):
        """Returns titles of articles to update and delete
        
        >>> mw_author_titles = Proxy.authors(cached_ok=False)
        >>> mw_articles = Proxy.articles_lastmod()
        >>> es_articles = Page.pages()
        >>> update,delete = Elasticsearch.articles_to_update(mw_author_titles, mw_articles, es_articles)
        
        @param mw_author_titles: list of author page titles
        @param mw_articles: list of MediaWiki author page dicts.
        @param es_articles: list of elastic.Page objects.
        @returns: (update,delete)
        """
        return Elasticsearch._new_update_deleted(
            {a['title']: a for a in mw_articles if a['title'] not in mw_author_titles},
            {a.title: a for a in es_articles}
        )
    
    @staticmethod
    def sources_to_update(ps_sources, es_sources):
        """Returns encyclopedia_ids of sources to update/delete
        
        @param ps_sources: list of PSMS sources
        @param es_sources: list of elastic.Source objects.
        @returns: (update,delete)
        """
        # sid:lastmod dict for comparisons
        ps_source_ids = {s.encyclopedia_id: s.modified for s in ps_sources}
        es_source_ids = {s.encyclopedia_id: s.modified for s in es_sources}
        # PSMS sources that are not in ES
        new = [
            encyclopedia_id
            for encyclopedia_id in ps_source_ids.keys()
            if not encyclopedia_id in es_source_ids.keys()
        ]
        # PSMS sources that are newer than ES sources
        updated = [
            encyclopedia_id
            for encyclopedia_id in es_source_ids.values()
            if ps_source_ids.get(encyclopedia_id) \
            and (ps_source_ids[encyclopedia_id] > es_source_ids[encyclopedia_id])
        ]
        # ES sources that are no longer in PSMS
        deleted = [
            encyclopedia_id
            for encyclopedia_id in es_source_ids.keys()
            if not encyclopedia_id in ps_source_ids.keys()
        ]
        return (new + updated, deleted)

    
    @staticmethod
    def authors_to_update(mw_author_titles, mw_articles, es_authors):
        """Returns titles of authors to add or delete
        
        Does not track updates because it's easy just to update them all.
        
        >>> mw_author_titles = Proxy.authors(cached_ok=False)
        >>> mw_articles = Proxy.articles_lastmod()
        >>> es_authors = Author.authors()
        >>> update,delete = Elasticsearch.authors_to_update(mw_author_titles, mw_articles, es_authors)
        
        @param mw_author_titles: list of author page titles
        @param mw_articles: list of MediaWiki author page dicts.
        @param es_authors: list of elastic.Author objects.
        @returns: (update,delete)
        """
        return Elasticsearch._new_update_deleted(
            {a['title']: a for a in mw_articles if a['title'] in mw_author_titles},
            {a.title: a for a in es_authors}
        )

    @staticmethod
    def update_all():
        """Check with Proxy source and update authors and articles.
        
        IMPORTANT: Will lock if unable to connect to MediaWiki server!
        """
        # authors
        mw_authors = Proxy.authors(cached_ok=False)
        es_authors = self.authors()
        authors_new,authors_delete = self.authors_to_update(mw_authors, es_authors)
        
        for n,title in enumerate(authors_delete):
            logging.debug('%s/%s %s' % (n, len(authors_delete), title))
            author = Author.get(url_title=title)
            author.delete()
            
        for n,title in enumerate(authors_new):
            logging.debug('%s/%s %s' % (n, len(authors_new), title))
            mwauthor = Proxy.page(title)
            author = Author.from_mw(mwauthor)
            author.save()
        
        # articles
        # authors need to be refreshed
        mw_authors = Proxy.authors(cached_ok=False)
        mw_articles = Proxy.articles_lastmod()
        es_authors = self.authors()
        es_articles = self.articles()
        articles_update,articles_delete = self.articles_to_update(
            mw_authors, mw_articles, es_authors, es_articles)
        self.delete_articles(titles=articles_delete)
        self.index_articles(titles=articles_update)
