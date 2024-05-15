import sys
from datetime import datetime
import time

import click
from elasticsearch.exceptions import NotFoundError

from elastictools.docstore import cluster as docstore_cluster

from encyc import config
from encyc import docstore
from encyc import http
from encyc import publish
from encyc import wiki
from encyc.repo_models import ELASTICSEARCH_CLASSES

SOURCES_API = config.SOURCES_API
MEDIAWIKI_API = config.MEDIAWIKI_API


class FakeSettings():
    def __init__(self, host):
        self.DOCSTORE_HOST = host
        self.DOCSTORE_SSL_CERTFILE = config.DOCSTORE_SSL_CERTFILE
        self.DOCSTORE_USERNAME = config.DOCSTORE_USERNAME
        self.DOCSTORE_PASSWORD = config.DOCSTORE_PASSWORD

def get_docstore(host=config.DOCSTORE_HOST):
    ds = docstore.DocstoreManager(
        docstore.INDEX_PREFIX, host, FakeSettings(host)
    )
    #try:
    #    ds.es.info()
    #except Exception as err:
    #    print(err)
    #    sys.exit(1)
    return ds


@click.group()
@click.option('--debug', is_flag=True)
def encyc(debug):
    """encyc - publish MediaWiki content to Elasticsearch; debug Elasticsearch
    
    \b
    Index Management: create, delete, reset
    Publishing:       authors, articles, sources, vocabs
    Debugging:        config, status, list, get
    
    By default the command uses DOCSTORE_HOST from the config file.  The tool will publish to at least two separate sites (Encyclopedia, Resource Guide), you can use the --hosts and --index options to override these values.
    
    \b
    SAMPLE CRON TASKS
      0,30 * * * * /usr/local/src/env/encyc/bin/encyc vocabs >> /var/log/encyc/core-syncwiki.log 2>&1
      1,31 * * * * /usr/local/src/env/encyc/bin/encyc authors >> /var/log/encyc/core-syncwiki.log 2>&1
      2,32 * * * * /usr/local/src/env/encyc/bin/encyc articles >> /var/log/encyc/core-syncwiki.log 2>&1
      12,42 * * * * /usr/local/src/env/encyc/bin/encyc sources >> /var/log/encyc/core-syncwiki.log 2>&1
    """
    pass


@encyc.command()
@click.option('--hosts','-h',
              default=config.DOCSTORE_HOST, envvar='DOCSTORE_HOST',
              help='Elasticsearch hosts.')
def conf(hosts):
    """Print configuration config.
    
    More detail since you asked.
    """
    ds = get_docstore(hosts)
    publish.print_configs(ds)


@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
def status(hosts):
    """Print status info.
    
    More detail since you asked.
    """
    ds = get_docstore(hosts)
    cluster = docstore_cluster(config.DOCSTORE_CLUSTERS, ds.host)
    try:
        check_es_status(ds)
        click.echo(f'Elasticsearch {ds.host} ({cluster}): OK')
        es = 1
    except:
        click.echo(f'Elasticsearch {ds.host} ({cluster}): ERROR')
        es = 0
    if es:
        try:
            click.echo(publish.status(ds))
        except NotFoundError as err:
            click.echo(err)
    click.echo('PSMS ({})'.format(SOURCES_API))
    try:
        check_psms_status()
        click.echo('ok')
        psms = 1
    except:
        click.echo('ERROR')
        psms = 0
    click.echo('MediaWiki ({})'.format(MEDIAWIKI_API))
    try:
        check_mediawiki_status()
        click.echo('ok')
        mw = 1
    except:
        click.echo('ERROR')
        mw = 0

@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
def create(hosts):
    """Create new indices.
    """
    ds = get_docstore(hosts)
    cluster = docstore_cluster(config.DOCSTORE_CLUSTERS, ds.host)
    click.echo(f'Creating indices in {ds.host} ({cluster})')
    #check_es_status(ds)
    publish.create_indices(ds)


@encyc.command()
@click.option('--confirm', is_flag=True, help='Yes I really want to destroy this database.')
@click.argument('host')
def destroy(confirm, host):
    """Delete indices (requires --confirm).
    
    \b
    It's meant to sound serious. Also to not clash with 'delete', which
    is for individual documents.
    """
    ds = get_docstore(host)
    cluster = docstore_cluster(config.DOCSTORE_CLUSTERS, ds.host)
    if confirm:
        click.echo(
            f"The {cluster} cluster ({ds.host}) with the following indices "
            + "will be DESTROYED!"
        )
        for index in ELASTICSEARCH_CLASSES['all']:
            click.echo(f"- {index['doc_type']}")
    else:
        click.echo(
            f"Add '--confirm' to destroy the {cluster} cluster ({ds.host})."
        )
        sys.exit(0)
    response = click.prompt(
        'Do you want to continue? [yes/no]', default='no', show_default=False
    )
    if response == 'yes':
        click.echo(f"Deleting indices from {ds.host} ({cluster}).")
        time.sleep(3)
        try:
            publish.delete_indices(ds)
        except Exception as err:
            logprint('error', err)
    else:
        click.echo("Cancelled.")


@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--indices','-i', help='Comma-separated list of indices to display.')
def mappings(hosts, indices):
    """Display mappings for the specified index/indices.
    """
    ds = get_docstore(hosts)
    check_es_status(ds)
    data = DOCSTORE.get_mappings()
    for key,val in data.items():
        if INDEX_PREFIX in key:
            click.echo('{}: {}'.format(key, val))


@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
def vocabs(hosts, report, dryrun, force):
    """TODO Index DDR vocabulary facets and terms.
    """
    ds = get_docstore(hosts)
    check_es_status(ds)
    publish.vocabs(ds, report=report, dryrun=dryrun, force=force)


@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
@click.option('--title', help='Single author to publish.')
def authors(hosts, report, dryrun, force, title):
    """Index authors.
    """
    ds = get_docstore(hosts)
    check_es_status(ds)
    check_es_index(ds, 'author')
    check_mediawiki_status()
    publish.authors(
        ds, report=report, dryrun=dryrun, force=force, title=title
    )


@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
@click.option('--title', help='Single article to publish.')
def articles(hosts, report, dryrun, force, title):
    """Index articles.
    """
    ds = get_docstore(hosts)
    check_es_status(ds)
    check_es_index(ds, 'article')
    check_psms_status()
    check_mediawiki_status()
    publish.articles(
        ds, report=report, dryrun=dryrun, force=force, title=title
    )


@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
@click.option('--sourceid', help='Single article to publish.')
def sources(hosts, report, dryrun, force, sourceid):
    """Index sources.
    """
    ds = get_docstore(hosts)
    check_es_status(ds)
    check_es_index(ds, 'source')
    check_psms_status()
    check_mediawiki_status()
    publish.sources(
        ds, report=report, dryrun=dryrun, force=force, psms_id=sourceid
    )


@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.argument('doctype')
def list(hosts, doctype):
    """List titles for all instances of specified doctype.
    """
    ds = get_docstore(hosts)
    check_es_status(ds)
    check_es_index(doctype)
    publish.listdocs(ds, doctype)


@encyc.command()
@click.argument('doctype')
@click.argument('object_id')
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--mediawiki', '-m', is_flag=True, default=False, help='Get from MediaWiki.')
@click.option('--raw', '-r', is_flag=True, default=False, help='Emit raw output.')
@click.option('--json', '-j', is_flag=True, default=False, help='Return ES record as JSON.')
@click.option('--body', '-b', default=False, help='Include body text.')
def get(hosts, mediawiki, raw, json, body, doctype, object_id):
    """Get a single record
    """
    ds = get_docstore(hosts)
    js = json
    import json  # this is kinda stupid
    data = {}
    if mediawiki:
        check_mediawiki_status()
        status_code,text = publish.Proxy._mw_page_text(object_id)
        if raw:
            click.echo(text)
            return
        if isinstance(data, Exception):
            click.echo(data)
            return
        data = json.loads(text)
        if not body:
            data['parse'].pop('text')
        if js:
            click.echo(json.dumps(data))
            return
        click.echo('source: Mediawiki')
        click.echo('title: {}'.format(data['parse'].pop('title')))
        for key,val in data['parse'].items():
            click.echo('{}: {}'.format(key, val))
    else:
        check_es_status(ds)
        check_es_index(ds, doctype)
        if raw:
            click.echo('Raw Elasticsearch output not yet implemented. Use wget?')
            return
        try:
            data = publish.get(ds, doctype, object_id, body)
        except NotFoundError as err:
            click.echo('ERROR: 404 Not Found - {} "{}"'.format(
                doctype, object_id
            ))
            sys.exit(1)
        if isinstance(data, Exception):
            click.echo(data)
            return
        for key,val in data.items():
            if isinstance(val, datetime):
                data[key] = val.isoformat()
        if data.get('body') and not body:
            data.pop('body')
        if js:
            click.echo(json.dumps(data))
            return
        click.echo('source: Elasticsearch')
        if doctype == 'article':
            click.echo('url_title: {}'.format(data.pop('url_title')))
            click.echo('title: {}'.format(data.pop('title')))
            description = data.pop('description')
            for key,val in data.items():
                click.echo('{}: {}'.format(key, val))
            click.echo('description: {}'.format(description))
        elif doctype == 'source':
            click.echo('psms_id: {}'.format(data.pop('psms_id')))
            click.echo('encyclopedia_id: {}'.format(data.pop('encyclopedia_id')))
            click.echo('created: {}'.format(data.pop('created')))
            click.echo('modified: {}'.format(data.pop('modified')))
            keys = sorted([key for key in data.keys()])
            for key in keys:
                click.echo('{}: {}'.format(key, data[key]))
        elif doctype == 'author':
            click.echo('title: {}'.format(data.pop('title')))
            click.echo('url_title: {}'.format(data.pop('url_title')))
            click.echo('title_sort: {}'.format(data.pop('title_sort')))
            for key,val in data.items():
                click.echo('{}: {}'.format(key, val))
            

@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--confirm', '-C', is_flag=True,
              help='Yes I really want to delete this index.')
@click.argument('doctype')
@click.argument('object_id')
def delete(hosts, confirm, doctype, object_id):
    """Delete a single record from Elasticsearch
    """
    ds = get_docstore(hosts)
    check_es_status(ds)
    check_es_index(ds, doctype)
    try:
        result = publish.delete(ds, doctype, object_id, confirm)
        click.echo(result)
    except NotFoundError as err:
        click.echo('ERROR: 404 Not Found - {} "{}"'.format(
            doctype, object_id
        ))


@encyc.command()
@click.argument('path')
@click.argument('title')
def parse(title, path):
    """Loads raw MediaWiki JSON from file, emits parsed HTML.
    
    \b
    Combine with `encyc get`:
    encyc get article "Nisei Progressives" -mr > /tmp/file.json
    encyc parse /tmp/file.json "Nisei Progressives"
    """
    click.echo(publish.parse(path, title))


@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
def test(hosts):
    """Load test data for encyc-front, encyc-rg
    """
    ds = get_docstore(hosts)
    check_es_status(ds)
    check_es_index(ds, 'article')
    check_es_index(ds, 'source')
    check_es_index(ds, 'author')
    check_psms_status()
    check_mediawiki_status()
    
    publish.articles(ds, force=1, title="Ansel Adams")
    publish.articles(ds, force=1, title="Aiko Herzig-Yoshinaga")
    publish.articles(ds, force=1, title="A.L. Wirin")
    publish.articles(ds, force=1, title="Amache (Granada)")
    publish.articles(ds, force=1, title="December 7, 1941")
    publish.articles(ds, force=1, title="Hawai'i")
    publish.articles(ds, force=1, title="Informants / \"inu\"")
    publish.authors(ds, force=1, title="Brian Niiya")
    publish.sources(ds, force=1, psms_id="en-littletokyousa-1")


def check_mediawiki_status():
    """Quit with message if cannot access Mediawiki API
    """
    status_code,reason = wiki.status_code()
    if status_code != 200:
        click.echo('ERROR: Mediawiki {} {}'.format(str(status_code), reason))
        sys.exit(1)

def check_psms_status():
    # yes events is not sources but if sources are 502 events will be too
    url = f'{SOURCES_API}/events/'
    r = http.get(url, headers={'content-type':'application/json'})
    if r.status_code != 200:
        click.echo('ERROR: PSMS {} {}'.format(str(r.status_code), r.reason))
        sys.exit(1)

def check_es_status(ds):
    """Quit with message if cannot access Elasticssearch
    """
    #try:
    #    DOCSTORE.start_test()
    #except docstore.TransportError as err:
    #    click.echo(f'ERROR: Elasticsearch cluster unavailable. ({DOCSTORE_HOST})')
    #    sys.exit(1)
    try:
        health = ds.health()
    except Exception as err:
        click.echo(f'ERROR: Elasticsearch {err}')
        sys.exit(1)

def check_es_index(ds, doctype):
    """Quit with message if Elasticssearch index not present
    """
    index_name = ds.index_name(doctype)
    if not ds.index_exists(index_name):
        click.echo('Elasticsearch: No index "{}".'.format(index_name))
        sys.exit(1)


@encyc.command()
@click.option('--hosts', default=config.DOCSTORE_HOST, help='Elasticsearch hosts.')
def databoxes(hosts):
    """Report on databoxes.
    """
    ds = get_docstore(hosts)
    check_es_status(ds)
    check_es_index(ds, 'article')
    check_mediawiki_status()
    publish.report_databoxes(ds)
