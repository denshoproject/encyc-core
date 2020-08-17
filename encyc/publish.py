import codecs
from datetime import datetime
from functools import wraps
import json
import logging
logger = logging.getLogger(__name__)
import os
import sys

from elasticsearch.exceptions import TransportError, NotFoundError, SerializationError

#from DDR import docstore
from encyc import config
from encyc import docstore
from encyc.models.legacy import Page as LegacyPage, Proxy
from encyc.models.elastic import Elasticsearch
from encyc.models.elastic import Author, Page, Source
from encyc.models.elastic import Facet, FacetTerm
from encyc import rsync
from encyc import wiki


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
    print('CONFIG_FILES:            %s' % config.CONFIG_FILES)
    print('')
    print('DOCSTORE_HOST:           %s' % config.DOCSTORE_HOST)
    print('MEDIAWIKI_API:           %s' % config.MEDIAWIKI_API)
    print('MEDIAWIKI_USERNAME:      %s' % config.MEDIAWIKI_API_USERNAME)
    print('MEDIAWIKI_PASSWORD:      %s' % config.MEDIAWIKI_API_PASSWORD)
    print('MEDIAWIKI_HTTP_USERNAME: %s' % config.MEDIAWIKI_HTTP_USERNAME)
    print('MEDIAWIKI_HTTP_PASSWORD: %s' % config.MEDIAWIKI_HTTP_PASSWORD)
    print('MEDIAWIKI_API_TIMEOUT:   %s' % config.MEDIAWIKI_API_TIMEOUT)
    print('SOURCES_API:             %s' % config.SOURCES_API)
    print('MEDIAWIKI_DATABOXES:     %s' % config.MEDIAWIKI_DATABOXES)
    print('HIDDEN_TAGS:             %s' % config.HIDDEN_TAGS)
    print('')

@stopwatch
def status(hosts):
    mw = wiki.MediaWiki()
    mw_author_titles = Proxy.authors(mw, cached_ok=False)
    mw_articles = Proxy.articles_lastmod(mw)
    num_mw_authors = len(mw_author_titles)
    num_mw_articles = len(mw_articles)
    num_es_authors = Author.authors().total
    num_es_articles = Page.pages().total
    num_es_sources = Source.sources().total
    pc_authors = float(num_es_authors) / num_mw_authors
    pc_articles = float(num_es_articles) / num_mw_articles
    logprint('debug', ' authors: {} of {} ({:.2%})'.format(
        num_es_authors, num_mw_authors, pc_authors,
    ))
    logprint('debug', 'articles: {} of {} ({:.2%})'.format(
        num_es_articles, num_mw_articles, pc_articles,
    ))
    logprint('debug', ' sources: %s' % num_es_sources)

@stopwatch
def delete_indices(hosts):
    try:
        statuses = docstore.Docstore(hosts).delete_indices()
        for status in statuses:
            logprint('debug', status)
    except Exception as err:
        logprint('error', err)
    
@stopwatch
def create_indices(hosts):
    try:
        statuses = docstore.Docstore(hosts).create_indices()
        for status in statuses:
            logprint('debug', status)
    except Exception as err:
        logprint('error', err)

def mappings(hosts):
    pass

@stopwatch
def authors(hosts, report=False, dryrun=False, force=False, title=None):
    mw = wiki.MediaWiki()
    ds = docstore.Docstore()
    logprint('debug', '------------------------------------------------------------------------')
    logprint('debug', 'getting mw_authors...')
    mw_author_titles = Proxy.authors(mw, cached_ok=False)
    mw_articles = Proxy.articles_lastmod(mw)
    logprint('debug', 'mediawiki authors: %s' % len(mw_author_titles))
    logprint('debug', 'getting es_authors...')
    es_authors = Author.authors()
    logprint('debug', 'elasticsearch authors: %s' % es_authors.total)
    
    if title:
        authors_new = [title]
    else:
        if force:
            logprint('debug', 'forcibly update all authors')
            authors_new = [page['title'] for page in es_authors.objects]
            authors_delete = []
        else:
            logprint('debug', 'determining new,delete...')
            authors_new,authors_delete = Elasticsearch.authors_to_update(
                mw_author_titles, mw_articles,
                es_authors.objects
            )
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
        mwauthor = LegacyPage.get(mw, title)
        try:
            existing_author = Author.get(title)
            logprint('debug', 'exists in elasticsearch')
        except:
            existing_author = None
        logprint('debug', 'creating author')
        author = Author.from_mw(mwauthor, author=existing_author)
        if not dryrun:
            logprint('debug', 'saving')
            out = author.save()
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
def articles(hosts, report=False, dryrun=False, force=False, title=None):
    logprint('debug', '------------------------------------------------------------------------')
    mw = wiki.MediaWiki()
    # authors need to be refreshed
    logprint('debug', 'getting mw_authors,articles...')
    mw_author_titles = Proxy.authors(mw, cached_ok=False)
    mw_articles = Proxy.articles_lastmod(mw)
    logprint('debug', 'getting es_articles...')
    es_articles = Page.pages()
    logprint('debug', 'mediawiki articles: %s' % len(mw_articles))
    logprint('debug', 'elasticsearch articles: %s' % es_articles.total)
    
    if title:
        articles_update = [title]
    else:
        if force:
            logprint('debug', 'forcibly update all articles')
            articles_update = [page['title'] for page in es_articles.objects]
            articles_delete = []
        else:
            logprint('debug', 'determining new,delete...')
            articles_update,articles_delete = Elasticsearch.articles_to_update(
                mw_author_titles, mw_articles,
                es_articles.objects
            )
        logprint('debug', 'articles to update: %s' % len(articles_update))
        #logprint('debug', 'articles to delete: %s' % len(articles_delete))
        if report:
            return
    
    logprint('debug', 'getting encycrg titles...')
    rg_titles = Page.rg_titles()
    logprint('debug', 'encycrg titles: %s' % len(rg_titles))
    if not len(rg_titles):
        logprint('info', 'NO ENCYC-RG ARTICLES!!!')
        logprint('info', 'RUN "encyc articles --force" AFTER THIS PASS TO MARK rg/notrg LINKS')
    
    logprint('debug', 'adding articles...')
    posted = 0
    could_not_post = []
    unpublished = []
    errors = []
    for n,title in enumerate(articles_update):
        logprint('debug', '--------------------')
        logprint('debug', '%s/%s %s' % (n+1, len(articles_update), title))
        logprint('debug', 'getting from mediawiki')
        mwpage = LegacyPage.get(mw, title, rg_titles=rg_titles)
        try:
            existing_page = Page.get(title)
            logprint('debug', 'exists in elasticsearch')
        except:
            existing_page = None
        
        if (mwpage.published or config.MEDIAWIKI_SHOW_UNPUBLISHED):
            
            logprint('debug', 'creating page')
            page = Page.from_mw(mwpage, page=existing_page)
            if not dryrun:
                logprint('debug', 'saving %s "%s"' % ('articles', page.url_title))
                try:
                    page.save()
                except SerializationError:
                    logprint('error', 'ERROR: Could not serialize to Elasticsearch!')
                try:
                    p = Page.get(title)
                except NotFoundError:
                    logprint('error', 'ERROR: Page(%s) NOT SAVED!' % title)
                    errors.append(title)
                logprint('debug', 'ok')
        
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
    if not len(rg_titles):
        logprint('info', 'NO ENCYC-RG ARTICLES!!!')
        logprint('info', 'RUN "encyc articles --force" AFTER THIS PASS TO MARK rg/notrg LINKS')
        logprint('info', 'NOTE: ENCYC-RG MUST BE ACCESSIBLE IN ORDER TO BUILD RG ARTICLES LIST.')
    logprint('debug', 'DONE')

@stopwatch
def sources(hosts, report=False, dryrun=False, force=False, psms_id=None):
    logprint(
        'debug',
        '------------------------------------------------------------------------')
    
    logprint('debug', 'getting sources from PSMS...')
    ps_sources = Proxy.sources_all()
    if ps_sources and isinstance(ps_sources, list):
        logprint('debug', 'psms sources: %s' % len(ps_sources))
    else:
        logprint('error', ps_sources)
    
    logprint('debug', 'getting sources from Elasticsearch...')
    es_sources = Source.sources()
    if es_sources and isinstance(es_sources, list):
        logprint('debug', 'es_sources: %s' % len(es_sources))
    else:
        logprint('error', 'error: %s' % es_sources)
    
    if psms_id:
        sources_update = [psms_id]
    else:
        if force:
            logprint('debug', 'forcibly update all sources')
            sources_update = [
                s.encyclopedia_id
                for s in ps_sources
                if s.encyclopedia_id
            ]
            sources_delete = []
        else:
            logprint('debug', 'crunching numbers...')
            sources_update,sources_delete = Elasticsearch.sources_to_update(
                ps_sources, es_sources.objects
            )
        logprint('debug', 'updates:   %s' % len(sources_update))
        logprint('debug', 'deletions: %s' % len(sources_delete))
        if report:
            return

    sources_by_id = {
        source.encyclopedia_id: source
        for source in ps_sources
    }
        
    logprint('debug', 'adding sources...')
    posted = 0
    to_rsync = []
    could_not_post = []
    unpublished = []
    errors = []
    for n,sid in enumerate(sources_update):
        logprint('debug', '--------------------')
        logprint('debug', '%s/%s %s' % (n+1, len(sources_update), sid))
        
        if not sid:
            continue
        
        ps_source = sources_by_id[sid]
        if not ps_source:
            logprint('debug', 'NOT AVAILABLE')
            could_not_post.append(sid)
            continue
        logprint('debug', ps_source)
        
        logprint('debug', 'getting from Elasticsearch')
        try:
            existing_source = Source.get()
            logprint('debug', existing_source)
        except:
            existing_source = None
            logprint('debug', 'not in ES')
        
        if (ps_source.published):
            
            es_source = Source.from_psms(ps_source)
            logprint('debug', es_source)
            if not dryrun:
                logprint('debug', 'saving')
                try:
                    es_source.save()
                except SerializationError:
                    logprint('error', 'ERROR: Could not serialize to Elasticsearch!')
                try:
                    s = Source.get(sid)
                except NotFoundError:
                    logprint('error', 'ERROR: Source(%s) NOT SAVED!' % sid)
                    errors.append(sid)
                
                # IMPORTANT! WE ASSUME THAT encyc-core RUNS ON SAME MACHINE AS PSMS!
                if es_source.original:
                    logprint('debug', 'original_path_abs %s' % es_source.original_path_abs)
                    to_rsync.append(es_source.original_path_abs)
                if es_source.display:
                    logprint('debug', 'display_path_abs %s' % es_source.display_path_abs)
                    to_rsync.append(es_source.display_path_abs)
                
                logprint('debug', 'ok')
        
        else:
            assert False
            # delete from ES if present
            if existing_page:
                logprint('debug', 'deleting...')
                existing_page.delete()
                unpublished.append(mwpage)

    # rsync source files to media server
    logprint('debug', '--------------------')
    logprint('debug', 'rsyncing')
    logprint('debug', '%s... -> %s' % (config.SOURCES_BASE, config.SOURCES_DEST))
    present_files = []
    missing_files = []
    while(to_rsync):
        path = to_rsync.pop()
        if os.path.exists(path):
            present_files.append(path)
            file_status = ''
        else:
            missing_files.append(path)
            file_status = '(missing)'
        logprint('debug', '- %s %s' % (path, file_status))
    
    if not dryrun:
        #if os.path.exists(path):
        result = rsync.push(
            present_files,
            config.SOURCES_DEST
        )
        logprint('debug', result)
        if result != '0':
            errors.append('Could not upload %s' % result)
        
    if could_not_post:
        logprint('debug', '========================================================================')
        logprint('debug', 'Could not post these: %s' % could_not_post)
    if unpublished:
        logprint('debug', '========================================================================')
        logprint('debug', 'Unpublished these: %s' % unpublished)
    if missing_files:
        logprint('debug', '========================================================================')
        logprint('debug', 'Files missing from local fs: %s' % missing_files)
    if errors:
        logprint('info', 'ERROR: %s titles were unpublishable:' % len(errors))
        for title in errors:
            logprint('info', 'ERROR: %s' % title)
    logprint('debug', 'DONE')

@stopwatch
def vocabs(hosts, report=False, dryrun=False, force=False):
    logprint('debug', '------------------------------------------------------------------------')
    logprint('debug', 'indexing facet terms...')
    facets = {}
    for f in config.DDR_VOCABS:
        logprint('debug', f)
        facet = Facet.retrieve(f)
        logprint('debug', facet)
        terms = facet.terms
        delattr(facet, 'terms')
        facet.save()
        for term in terms:
            logprint('debug', '- %s' % term)
            term.save()
        
    logprint('debug', 'DONE')

def listdocs(hosts, doctype):
    if   doctype == 'article': results = Page.pages()
    elif doctype == 'author': results = Author.authors()
    elif doctype == 'source': results = Source.sources()
    else:
        logprint('error', '"%s" is not a recognized doc_type!' % doctype)
        return
    total = results.total
    for n,r in enumerate(results.objects):
        if doctype == 'source':
            print('%s/%s| %s' % (n, total, r.encyclopedia_id))
        else:
            print('%s/%s| %s' % (n, total, r.title))

def get(doctype, object_id, body=False):
    """
    @param doctype
    @param object_id
    @param body: bool Include body text
    """
    if   doctype == 'article':
        return Page.get(object_id).to_dict()
    elif doctype == 'author':
        return Author.get(object_id).to_dict()
    elif doctype == 'source':
        return Source.get(object_id).to_dict()
    return {'error': 'Unknown doctype: "{}"'.format(doctype)}

def delete(doctype, object_id, confirm=False):
    if not confirm:
        return {'error': 'Confirmation required.'}
    if   doctype == 'article':
        o = Page.get(object_id)
        return o.delete()
    elif doctype == 'author':
        o = Author.get(object_id)
        return o.delete()
    elif doctype == 'source':
        o = Source.get(object_id)
        return o.delete()
    return {'error': '"{}" is not a recognized doc_type!'.format(doctype)}

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
    text = LegacyPage.pagedata(title)
    data = json.loads(text)
    pretty = format_json(data)
    write_text(pretty, path)

def parse(path, title):
    """Loads raw MediaWiki JSON from file, emits parsed HTML.
    
    For testing the parser without having to hit the MediaWiki API each time,
    and without risk of modifying original data in mediawiki.
    Protip: combine with `encyc get DOCTYPE TITLE --json`.
    
    @param title: str
    @param path: str
    """
    mw = wiki.MediaWiki()
    #path_html = os.path.splitext(path)[0] + '.html'
    text = read_text(path)
    mwpage = LegacyPage.get(mw, title)
    #write_text(mwpage.body, path_html)
    return mwpage.body
