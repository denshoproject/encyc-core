import sys
from datetime import datetime

import click
from elasticsearch.exceptions import NotFoundError

from encyc import config
from encyc import docstore
from encyc import publish
from encyc import wiki

DOCSTORE_HOST = config.DOCSTORE_HOST
MEDIAWIKI_API = config.MEDIAWIKI_API


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
def config():
    """Print configuration settings.
    
    More detail since you asked.
    """
    publish.print_configs()


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
def status(hosts):
    """Print status info.
    
    More detail since you asked.
    """
    try:
        check_es_status()
        click.echo('Elasticsearch: OK')
        es = 1
    except:
        click.echo('Elasticsearch ({}): ERROR'.format(DOCSTORE_HOST))
        es = 0
    if es:
        try:
            click.echo(publish.status(hosts))
        except NotFoundError as err:
            click.echo(err)
    try:
        check_mediawiki_status()
        click.echo('MediaWiki: OK')
        mw = 1
    except:
        click.echo('ERROR: Mediawiki ({})'.format(MEDIAWIKI_API))
        mw = 0

@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
def create(hosts):
    """Create new indices.
    """
    check_es_status()
    check_mediawiki_status()
    publish.create_indices(hosts)


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--confirm', is_flag=True,
              help='Yes I really want to delete this index.')
def destroy(hosts, confirm):
    """Delete indices (requires --confirm).
    """
    check_es_status()
    check_mediawiki_status()
    if confirm:
        publish.delete_indices(hosts)
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--indices','-i', help='Comma-separated list of indices to display.')
def mappings(hosts, indices):
    """Display mappings for the specified index/indices.
    """
    check_es_status()
    data = docstore.Docstore(hosts).get_mappings()
    for key,val in data.items():
        if docstore.INDEX_PREFIX in key:
            click.echo('{}: {}'.format(key, val))


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
def vocabs(hosts, report, dryrun, force):
    """TODO Index DDR vocabulary facets and terms.
    """
    check_es_status()
    check_mediawiki_status()
    publish.vocabs(hosts=hosts, report=report, dryrun=dryrun, force=force)


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
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
    check_es_status()
    check_es_index('author')
    check_mediawiki_status()
    publish.authors(
        hosts=hosts, report=report, dryrun=dryrun, force=force, title=title
    )


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
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
    check_es_status()
    check_es_index('article')
    check_mediawiki_status()
    publish.articles(
        hosts=hosts, report=report, dryrun=dryrun, force=force, title=title
    )


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
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
    check_es_status()
    check_es_index('source')
    check_mediawiki_status()
    publish.sources(
        hosts=hosts, report=report, dryrun=dryrun, force=force, psms_id=sourceid
    )


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.argument('doctype')
def list(hosts, doctype):
    """List titles for all instances of specified doctype.
    """
    check_es_status()
    check_es_index(doctype)
    publish.listdocs(hosts, doctype)


@encyc.command()
@click.argument('doctype')
@click.argument('object_id')
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--mediawiki', '-m', is_flag=True, default=False, help='Get from MediaWiki.')
@click.option('--raw', '-r', is_flag=True, default=False, help='Emit raw output.')
@click.option('--json', '-j', is_flag=True, default=False, help='Return ES record as JSON.')
@click.option('--body', '-b', default=False, help='Include body text.')
def get(hosts, mediawiki, raw, json, body, doctype, object_id):
    """Get a single record
    """
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
        check_es_status()
        check_es_index(doctype)
        if raw:
            click.echo('Raw Elasticsearch output not yet implemented. Use wget?')
            return
        try:
            data = publish.get(doctype, object_id, body)
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
@click.option('--confirm', '-C', is_flag=True,
              help='Yes I really want to delete this index.')
@click.argument('doctype')
@click.argument('object_id')
def delete(confirm, doctype, object_id):
    """Delete a single record from Elasticsearch
    """
    check_es_status()
    check_es_index(doctype)
    check_mediawiki_status()
    try:
        result = publish.delete(doctype, object_id, confirm)
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
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
def test(hosts):
    """Load test data for encyc-front, encyc-rg
    """
    check_es_status()
    check_es_index('article')
    check_es_index('source')
    check_es_index('author')
    check_mediawiki_status()
    
    publish.articles(hosts=hosts, force=1, title="Ansel Adams")
    publish.articles(hosts=hosts, force=1, title="Aiko Herzig-Yoshinaga")
    publish.articles(hosts=hosts, force=1, title="A.L. Wirin")
    publish.articles(hosts=hosts, force=1, title="Amache (Granada)")
    publish.articles(hosts=hosts, force=1, title="December 7, 1941")
    publish.articles(hosts=hosts, force=1, title="Hawai'i")
    publish.articles(hosts=hosts, force=1, title="Informants / \"inu\"")
    publish.authors(hosts=hosts, force=1, title="Brian Niiya")
    publish.sources(hosts=hosts, force=1, psms_id="en-littletokyousa-1")


def check_mediawiki_status():
    """Quit with message if cannot access Mediawiki API
    """
    status_code,reason = wiki.status_code()
    if status_code != 200:
        click.echo('ERROR: Mediawiki {} {}'.format(str(status_code), reason))
        sys.exit(1)

def check_es_status():
    """Quit with message if cannot access Elasticssearch
    """
    try:
        docstore.Docstore().start_test()
    except docstore.TransportError as err:
        click.echo('ERROR: Elasticsearch cluster unavailable. ({})'.format(
            DOCSTORE_HOST
        ))
        sys.exit(1)

def check_es_index(doctype):
    """Quit with message if Elasticssearch index not present
    """
    ds = docstore.Docstore()
    if doctype:
        index_name = ds.index_name(doctype)
        if not ds.index_exists(index_name):
            click.echo('Elasticsearch: No index "{}".'.format(index_name))
            sys.exit(1)
