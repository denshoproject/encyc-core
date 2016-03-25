from datetime import datetime
import logging
logger = logging.getLogger(__name__)
import sys

from elasticsearch_dsl import Index, DocType, String
from elasticsearch_dsl.connections import connections
from elasticsearch.exceptions import NotFoundError

#from DDR import docstore
#from wikiprox import encyclopedia
from encyc import config
from encyc import docstore
from encyc.models.legacy import Proxy
from encyc.models import Elasticsearch
from encyc.models import Author, Page, Source


def logprint(level, msg):
    print('%s %s' % (datetime.now(), msg))
    if   level == 'debug': logging.debug(msg)
    elif level == 'info': logging.info(msg)
    elif level == 'error': logging.error(msg)

def print_configs():
    print('manage.py encyc commands will use the following settings:')
    print('')
    print('DOCSTORE_HOSTS:         %s' % config.DOCSTORE_HOSTS)
    print('DOCSTORE_INDEX:         %s' % config.DOCSTORE_INDEX)
    print('MEDIAWIKI_HTML:         %s' % config.MEDIAWIKI_HTML)
    print('MEDIAWIKI_API:          %s' % config.MEDIAWIKI_API)
    print('MEDIAWIKI_API_USERNAME: %s' % config.MEDIAWIKI_API_USERNAME)
    print('MEDIAWIKI_API_PASSWORD: %s' % config.MEDIAWIKI_API_PASSWORD)
    print('MEDIAWIKI_API_TIMEOUT:  %s' % config.MEDIAWIKI_API_TIMEOUT)
    print('')

def set_hosts_index():
    logprint('debug', 'hosts: %s' % config.DOCSTORE_HOSTS)
    connections.create_connection(hosts=config.DOCSTORE_HOSTS)
    logprint('debug', 'index: %s' % config.DOCSTORE_INDEX)
    index = Index(config.DOCSTORE_INDEX)
    return index
    
def delete_index():
    index = set_hosts_index()
    logprint('debug', 'deleting old index')
    try:
        index.delete()
    except NotFoundError:
        logprint('error', 'ERROR: Index does not exist!')
    logprint('debug', 'DONE')
    
def create_index():
    index = set_hosts_index()
    logprint('debug', 'creating new index')
    index = Index(config.DOCSTORE_INDEX)
    index.create()
    logprint('debug', 'creating mappings')
    Author.init()
    Page.init()
    Source.init()
    logprint('debug', 'registering doc types')
    index.doc_type(Author)
    index.doc_type(Page)
    index.doc_type(Source)
    logprint('debug', 'DONE')

def authors(report=False, dryrun=False, force=False):
    index = set_hosts_index()

    logprint('debug', '------------------------------------------------------------------------')
    logprint('debug', 'getting mw_authors...')
    mw_author_titles = Proxy().authors(cached_ok=False)
    mw_articles = Proxy().articles_lastmod()
    logprint('debug', 'getting es_authors...')
    es_authors = Author.authors()
    if force:
        logprint('debug', 'forcibly update all authors')
        authors_new = [page['title'] for page in es_authors]
        authors_delete = []
    else:
        logprint('debug', 'determining new,delete...')
        authors_new,authors_delete = Elasticsearch.authors_to_update(
            mw_author_titles, mw_articles, es_authors)
    logprint('debug', 'mediawiki authors: %s' % len(mw_author_titles))
    logprint('debug', 'authors to add: %s' % len(authors_new))
    logprint('debug', 'authors to delete: %s' % len(authors_delete))
    if report:
        return
    
    logprint('debug', 'deleting...')
    for n,title in enumerate(authors_delete):
        logprint('debug', '--------------------')
        logprint('debug', '%s/%s %s' % (n, len(authors_delete), title))
        author = Author.get(title)
        if not dryrun:
            author.delete()
     
    logprint('debug', 'adding...')
    for n,title in enumerate(authors_new):
        logprint('debug', '--------------------')
        logprint('debug', '%s/%s %s' % (n, len(authors_new), title))
        logprint('debug', 'getting from mediawiki')
        mwauthor = Proxy().page(title)
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
    
    logprint('debug', 'DONE')

def articles(report=False, dryrun=False, force=False):
    index = set_hosts_index()
    
    logprint('debug', '------------------------------------------------------------------------')
    # authors need to be refreshed
    logprint('debug', 'getting mw_authors,articles...')
    mw_author_titles = Proxy().authors(cached_ok=False)
    mw_articles = Proxy().articles_lastmod()
    logprint('debug', 'getting es_articles...')
    es_articles = Page.pages()
    if force:
        logprint('debug', 'forcibly update all articles')
        articles_update = [page['title'] for page in es_articles]
        articles_delete = []
    else:
        logprint('debug', 'determining new,delete...')
        articles_update,articles_delete = Elasticsearch.articles_to_update(
            mw_author_titles, mw_articles, es_articles)
    logprint('debug', 'mediawiki articles: %s' % len(mw_articles))
    logprint('debug', 'elasticsearch articles: %s' % len(es_articles))
    logprint('debug', 'articles to update: %s' % len(articles_update))
    logprint('debug', 'articles to delete: %s' % len(articles_delete))
    if report:
        return
    
    logprint('debug', 'adding articles...')
    posted = 0
    could_not_post = []
    for n,title in enumerate(articles_update):
        logprint('debug', '--------------------')
        logprint('debug', '%s/%s %s' % (n+1, len(articles_update), title))
        logprint('debug', 'getting from mediawiki')
        mwpage = Proxy().page(title)
        try:
            existing_page = Page.get(title)
            logprint('debug', 'exists in elasticsearch')
        except:
            existing_page = None
        if (mwpage.published or config.MEDIAWIKI_SHOW_UNPUBLISHED):
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
                page.save()
                try:
                    p = Page.get(title)
                except NotFoundError:
                    logprint('error', 'ERROR: Page(%s) NOT SAVED!' % title)
        else:
            logprint('debug', 'not publishable: %s' % mwpage)
            could_not_post.append(mwpage)
    
    if could_not_post:
        logprint('debug', '========================================================================')
        logprint('debug', 'Could not post these: %s' % could_not_post)
    logprint('debug', 'DONE')

def topics(report=False, dryrun=False, force=False):
    index = set_hosts_index()

    logprint('debug', '------------------------------------------------------------------------')
    logprint('debug', 'indexing topics...')
    Elasticsearch.index_topics()
    logprint('debug', 'DONE')
