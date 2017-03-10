import codecs
from datetime import datetime
from functools import wraps
import json
import logging
logger = logging.getLogger(__name__)
import os
import sys

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import TransportError, NotFoundError, SerializationError
from elasticsearch_dsl import Index, DocType, String
from elasticsearch_dsl import Search
from elasticsearch_dsl.connections import connections

#from DDR import docstore
from encyc import config
from encyc import docstore
from encyc.models.legacy import Proxy
from encyc.models import Elasticsearch
from encyc.models import Author, Page, Source


def stopwatch(fn):
    """Decorator for print elapsed time of operations.
    """
    @wraps(fn)
    def with_profiling(*args, **kwargs):
        start = datetime.now()
        result = fn(*args, **kwargs)
        elapsed = datetime.now() - start
        logprint('debug', 'TIME: %s' % elapsed)
        return result
    return with_profiling

def read_text(path):
    """Read text file; make sure text is in UTF-8.
    
    @param path: str Absolute path to file.
    @returns: unicode
    """
    with codecs.open(path, 'rU', 'utf-8') as f:  # the 'U' is for universal-newline mode
        text = f.read()
    return text

def write_text(text, path):
    """Write text to UTF-8 file.
    
    @param text: unicode
    @param path: str Absolute path to file.
    """
    with codecs.open(path, 'wb', 'utf-8') as f:
        f.write(text)

def logprint(level, msg):
    try:
        print('%s %s' % (datetime.now(), msg))
    except UnicodeEncodeError:
        print('ERROR: UnicodeEncodeError')
    if   level == 'debug': logging.debug(msg)
    elif level == 'info': logging.info(msg)
    elif level == 'error': logging.error(msg)

def format_json(data):
    """Write JSON using consistent formatting and sorting.
    
    For versioning and history to be useful we need data fields to be written
    in a format that is easy to edit by hand and in which values can be compared
    from one commit to the next.  This function prints JSON with nice spacing
    and indentation and with sorted keys, so fields will be in the same relative
    position across commits.
    
    >>> data = {'a':1, 'b':2}
    >>> path = '/tmp/ddrlocal.models.write_json.json'
    >>> write_json(data, path)
    >>> with open(path, 'r') as f:
    ...     print(f.readlines())
    ...
    ['{\n', '    "a": 1,\n', '    "b": 2\n', '}']
    """
    return json.dumps(data, indent=4, separators=(',', ': '), sort_keys=True)

def print_configs():
    print('manage.py encyc commands will use the following settings:')
    print('CONFIG_FILES:           %s' % config.CONFIG_FILES)
    print('')
    print('DOCSTORE_HOSTS:         %s' % config.DOCSTORE_HOSTS)
    print('DOCSTORE_INDEX:         %s' % config.DOCSTORE_INDEX)
    print('MEDIAWIKI_API:          %s' % config.MEDIAWIKI_API)
    print('MEDIAWIKI_API_USERNAME: %s' % config.MEDIAWIKI_API_USERNAME)
    print('MEDIAWIKI_API_PASSWORD: %s' % config.MEDIAWIKI_API_PASSWORD)
    print('MEDIAWIKI_API_HTUSER:   %s' % config.MEDIAWIKI_API_HTUSER)
    print('MEDIAWIKI_API_HTPASS:   %s' % config.MEDIAWIKI_API_HTPASS)
    print('MEDIAWIKI_API_TIMEOUT:  %s' % config.MEDIAWIKI_API_TIMEOUT)
    print('SOURCES_API:            %s' % config.SOURCES_API)
    print('HIDDEN_TAGS:            %s' % config.HIDDEN_TAGS)
    print('')

def set_hosts_index(hosts=config.DOCSTORE_HOSTS, index=config.DOCSTORE_INDEX):
    logprint('debug', 'hosts: %s' % hosts)
    connections.create_connection(hosts=hosts)
    logprint('debug', 'index: %s' % index)
    return Index(index)

@stopwatch
def status(hosts, index):
    """
"indices": {
    "encyc-production": {
        "index": {
            "primary_size_in_bytes": ​1746448,
            "size_in_bytes": ​1746448
        },
        "docs": {
            "num_docs": ​247,
            "max_doc": ​247,
            "deleted_docs": ​0
        },

from elasticsearch import Elasticsearch
client = Elasticsearch()
client.info()
s = client.indices.stats()

format_json(client.indices.stats('encyc-production'))


    """
    logprint('debug', '------------------------------------------------------------------------')
    logprint('debug', 'MediaWiki')
    logprint('debug', ' MEDIAWIKI_API: %s' % config.MEDIAWIKI_API)
    mw_author_titles = Proxy.authors(cached_ok=False)
    mw_articles = Proxy.articles_lastmod()
    num_mw_authors = len(mw_author_titles)
    num_mw_articles = len(mw_articles)
    logprint('debug', '       authors: %s' % num_mw_authors)
    logprint('debug', '      articles: %s' % num_mw_articles)
    
    logprint('debug', '------------------------------------------------------------------------')
    logprint('debug', 'Elasticsearch')
    logprint('debug', 'DOCSTORE_HOSTS (default): %s' % config.DOCSTORE_HOSTS)
    logprint('debug', 'DOCSTORE_INDEX (default): %s' % config.DOCSTORE_INDEX)
    if hosts != config.DOCSTORE_HOSTS:
        logprint('debug', 'docstore_hosts: %s' % hosts)
    if index != config.DOCSTORE_INDEX:
        logprint('debug', 'docstore_index: %s' % index)
    
    i = set_hosts_index(hosts=hosts, index=index)
    es = i.connection
    
    try:
        pingable = es.ping()
        if not pingable:
            logprint('error', "Can't ping the cluster!")
            return
    except elasticsearch.exceptions.ConnectionError:
        logprint('error', "Connection error when trying to ping the cluster!")
        return
    logprint('debug', 'ping ok')
    
    if es.indices.exists(index=index):
        logprint('debug', '%s present' % index)
    else:
        logprint('error', "Index '%s' doesn't exist!" % index)
        return
    
    num_es_authors = len(Author.authors())
    num_es_articles = len(Page.pages())
    pc_authors = float(num_es_authors) / num_mw_authors
    pc_articles = float(num_es_articles) / num_mw_articles
    logprint('debug', '       authors: {}/{} {:.2%}'.format(
        num_es_authors, num_mw_authors, pc_authors,
    ))
    logprint('debug', '      articles: {}/{} {:.2%}'.format(
        num_es_articles, num_mw_articles, pc_articles,
    ))
    logprint('debug', '       sources: %s' % len(Source.sources()))

@stopwatch
def delete_index(hosts, index):
    i = set_hosts_index(hosts=hosts, index=index)
    logprint('debug', 'deleting old index')
    try:
        i.delete()
    except NotFoundError:
        logprint('error', 'ERROR: Index does not exist!')
    logprint('debug', 'DONE')
    
@stopwatch
def create_index(hosts, index):
    i = set_hosts_index(hosts=hosts, index=index)
    logprint('debug', 'creating new index')
    i = Index(index)
    i.create()
    logprint('debug', 'registering doc types')
    i.doc_type(Author)
    i.doc_type(Page)
    i.doc_type(Source)
    logprint('debug', 'DONE')

@stopwatch
def delete_alias(hosts, index, alias):
    i = set_hosts_index(hosts=hosts, index=index)
    result = i.connection.indices.delete_alias(index=index, name=alias)
    logprint('debug', result)
    logprint('debug', 'DONE')
    
@stopwatch
def create_alias(hosts, index, alias):
    logprint('debug', 'creating alias "%s"' % alias)
    i = set_hosts_index(hosts=hosts, index=index)
    result = i.connection.indices.put_alias(index=index, name=alias)
    logprint('debug', result)
    logprint('debug', 'DONE')

def push_mappings(hosts, index, mappings_path):
    """Pushes mappings from file into ES.
    
    @param path: Absolute path to dir containing facet files.
    @param mappings_path: Absolute path to mappings JSON.
    @returns: JSON dict with status code and response
    """
    logprint('debug', 'mappings')
    i = set_hosts_index(hosts=hosts, index=index)
    es = i.connection
    print i
    print es
    with open(mappings_path, 'r') as f:
        mappings = json.loads(f.read())
    statuses = []
    for mapping in mappings:
        model = mapping.keys()[0]
        status = es.indices.put_mapping(
            index=index,
            doc_type=model,
            body=mapping[model],
        )
        statuses.append( {'model':model, 'status':status} )
    #self.mappings = mappings_list
    return statuses

@stopwatch
def authors(hosts, index, report=False, dryrun=False, force=False, title=None):
    i = set_hosts_index(hosts=hosts, index=index)

    logprint('debug', '------------------------------------------------------------------------')
    logprint('debug', 'getting mw_authors...')
    mw_author_titles = Proxy.authors(cached_ok=False)
    mw_articles = Proxy.articles_lastmod()
    logprint('debug', 'getting es_authors...')
    es_authors = Author.authors()
    logprint('debug', 'mediawiki authors: %s' % len(mw_author_titles))
    
    if title:
        authors_new = [title]
    else:
        if force:
            logprint('debug', 'forcibly update all authors')
            authors_new = [page['title'] for page in es_authors]
            authors_delete = []
        else:
            logprint('debug', 'determining new,delete...')
            authors_new,authors_delete = Elasticsearch.authors_to_update(
                mw_author_titles, mw_articles, es_authors)
        logprint('debug', 'authors to add: %s' % len(authors_new))
        #logprint('debug', 'authors to delete: %s' % len(authors_delete))
        if report:
            return
    
    #logprint('debug', 'deleting...')
    #for n,title in enumerate(authors_delete):
    #    logprint('debug', '--------------------')
    #    logprint('debug', '%s/%s %s' % (n, len(authors_delete), title))
    #    author = Author.get(title=title)
    #    if not dryrun:
    #        author.delete()
     
    logprint('debug', 'adding...')
    errors = []
    for n,title in enumerate(authors_new):
        logprint('debug', '--------------------')
        logprint('debug', '%s/%s %s' % (n, len(authors_new), title))
        logprint('debug', 'getting from mediawiki')
        mwauthor = Proxy.page(title, index=index)
        try:
            existing_author = Author.get(title)
            logprint('debug', 'exists in elasticsearch')
        except:
            existing_author = None
        logprint('debug', 'creating author')
        author = Author.from_mw(mwauthor, author=existing_author)
        if not dryrun:
            logprint('debug', 'saving')
            author.save()
            try:
                a = Author.get(title)
            except NotFoundError:
                logprint('error', 'ERROR: Author(%s) NOT SAVED!' % title)
                errors.append(title)
    if errors:
        logprint('info', 'ERROR: %s titles were unpublishable:' % len(errors))
        for title in errors:
            logprint('info', 'ERROR: %s' % title)
    logprint('debug', 'DONE')

@stopwatch
def articles(hosts, index, report=False, dryrun=False, force=False, title=None):
    i = set_hosts_index(hosts=hosts, index=index)
    
    logprint('debug', '------------------------------------------------------------------------')
    # authors need to be refreshed
    logprint('debug', 'getting mw_authors,articles...')
    mw_author_titles = Proxy.authors(cached_ok=False)
    mw_articles = Proxy.articles_lastmod()
    logprint('debug', 'getting es_articles...')
    es_articles = Page.pages()
    logprint('debug', 'mediawiki articles: %s' % len(mw_articles))
    logprint('debug', 'elasticsearch articles: %s' % len(es_articles))
    
    if title:
        articles_update = [title]
    else:
        if force:
            logprint('debug', 'forcibly update all articles')
            articles_update = [page['title'] for page in es_articles]
            articles_delete = []
        else:
            logprint('debug', 'determining new,delete...')
            articles_update,articles_delete = Elasticsearch.articles_to_update(
                mw_author_titles, mw_articles, es_articles)
        logprint('debug', 'articles to update: %s' % len(articles_update))
        #logprint('debug', 'articles to delete: %s' % len(articles_delete))
        if report:
            return
    
    logprint('debug', 'adding articles...')
    posted = 0
    could_not_post = []
    unpublished = []
    errors = []
    for n,title in enumerate(articles_update):
        logprint('debug', '--------------------')
        logprint('debug', '%s/%s %s' % (n+1, len(articles_update), title))
        logprint('debug', 'getting from mediawiki')
        mwpage = Proxy.page(title)
        try:
            existing_page = Page.get(title)
            logprint('debug', 'exists in elasticsearch')
        except:
            existing_page = None

        if (mwpage.published or config.MEDIAWIKI_SHOW_UNPUBLISHED):
            # publish
            page_sources = [source['encyclopedia_id'] for source in mwpage.sources]
            for mwsource in mwpage.sources:
                logprint('debug', '- source %s' % mwsource['encyclopedia_id'])
                source = Source.from_mw(mwsource, title)
                if not dryrun:
                    source.save()
            logprint('debug', 'creating page')
            page = Page.from_mw(mwpage, page=existing_page)
            if not dryrun:
                logprint('debug', 'saving')
                try:
                    page.save()
                except SerializationError:
                    logprint('error', 'ERROR: Could not serialize to Elasticsearch!')
                try:
                    p = Page.get(title)
                except NotFoundError:
                    logprint('error', 'ERROR: Page(%s) NOT SAVED!' % title)
                    errors.append(title)
        
        else:
            # delete from ES if present
            logprint('debug', 'not publishable: %s' % mwpage)
            if existing_page:
                logprint('debug', 'deleting...')
                existing_page.delete()
                unpublished.append(mwpage)
    
    if could_not_post:
        logprint('debug', '========================================================================')
        logprint('debug', 'Could not post these: %s' % could_not_post)
    if unpublished:
        logprint('debug', '========================================================================')
        logprint('debug', 'Unpublished these: %s' % unpublished)
    if errors:
        logprint('info', 'ERROR: %s titles were unpublishable:' % len(errors))
        for title in errors:
            logprint('info', 'ERROR: %s' % title)
    logprint('debug', 'DONE')

@stopwatch
def topics(hosts, index, report=False, dryrun=False, force=False):
    i = set_hosts_index(hosts=hosts, index=index)

    logprint('debug', '------------------------------------------------------------------------')
    logprint('debug', 'indexing topics...')
    Elasticsearch.index_topics()
    logprint('debug', 'DONE')


DOC_TYPES = [
    'articles',
    'authors',
    'sources',
]

def listdocs(hosts, index, doctype):
    i = set_hosts_index(hosts=hosts, index=index)
    if doctype not in DOC_TYPES:
        logprint('error', '"%s" is not a recognized doc_type!' % doctype)
        return
    if   doctype == 'articles': s = Page.search()
    elif doctype == 'authors': s = Author.search()
    elif doctype == 'sources': s = Source.search()
    results = s.execute()
    total = len(results)
    for n,r in enumerate(results):
        print('%s/%s| %s' % (n, total, r.__repr__()))

def get(hosts, index, doctype, identifier):
    i = set_hosts_index(hosts=hosts, index=index)
    if doctype not in DOC_TYPES:
        logprint('error', '"%s" is not a recognized doc_type!' % doctype)
        return
    print('doctype "%s"' % doctype)
    print('identifier "%s"' % identifier)
    
    if   doctype == 'articles':
        o = None
        try:
            o = Page.get(identifier)
        except TransportError as e:
            print(e)
        if o:
            print(o.__repr__())
            print('TITLE: "%s"' % o.title)
            print('--------------------')
            print(o.body)
            print('--------------------')
    
    elif doctype == 'authors':
        o = None
        try:
            o = Author.get(identifier)
        except TransportError as e:
            print(e)
        if o:
            print(o.__repr__())
            _print_dict(o.to_dict())
    
    elif doctype == 'sources':
        o = None
        try:
            o = Source.get(identifier)
        except TransportError as e:
            print(e)
        if o:
            print(o.__repr__())
            _print_dict(o.to_dict())

def _print_dict(d):
    keys = d.keys()
    keys.sort()
    width = 0
    for key in keys:
        if len(key) > width:
            width = len(key)
    for key in keys:
        print('%s: "%s"' % (
            key.ljust(width,' '),
            d[key]
        ))


def _dumpjson(title, path):
    """Gets page text from MediaWiki and dumps to file.
    
    @param title: str
    @param path: str
    """
    text = Proxy._mw_page_text(title)
    data = json.loads(text)
    pretty = format_json(data)
    write_text(pretty, path)

def _parse(title, path):
    """Loads page json from file, generates Page, saves HTML to file.
    
    The idea here is to parse text from a local file,
    not hit Mediawiki each time
    also, to manipulate the text without changing original data in mediawiki
    
    @param title: str
    @param path: str
    """
    path_html = os.path.splitext(path)[0] + '.html'
    text = read_text(path)
    mwpage = Proxy._mkpage(title, 200, text)
    write_text(mwpage.body, path_html)
