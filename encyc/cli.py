from datetime import datetime

import click

from encyc import config
from encyc import docstore
from encyc import publish

DOCSTORE_HOST = config.DOCSTORE_HOST


@click.group()
@click.option('--debug', is_flag=True)
def encyc(debug):
    """encyc - publish MediaWiki content to Elasticsearch; debug Elasticsearch
    
    \b
    Index Management: create, delete, reset
    Publishing:       topics, authors, articles, sources
    Debugging:        config, status, list, get
    
    By default the command uses DOCSTORE_HOST from the config file.  The tool will publish to at least two separate sites (Encyclopedia, Resource Guide), you can use the --hosts and --index options to override these values.
    
    \b
    SAMPLE CRON TASKS
      0,30 * * * * /usr/local/src/env/encyc/bin/encyc topics >> /var/log/encyc/core-syncwiki.log 2>&1
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
    publish.status(hosts)


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
def create(hosts):
    """Create new indices.
    """
    publish.create_indices(hosts)


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--confirm', is_flag=True,
              help='Yes I really want to delete this index.')
def destroy(hosts, confirm):
    """Delete indices (requires --confirm).
    """
    if confirm:
        publish.delete_indices(hosts)
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--confirm', is_flag=True,
              help='Yes I really want to delete this index.')
def reset(hosts, confirm):
    """Delete existing index and create new one (requires --confirm).
    """
    if confirm:
        publish.delete_indices(hosts)
        publish.create_indices(hosts)
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--indices','-i', help='Comma-separated list of indices to display.')
def mappings(hosts, indices):
    """Display mappings for the specified index/indices.
    """
    data = docstore.Docstore(hosts).get_mappings()
    for key,val in data.iteritems():
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
def topics(hosts, report, dryrun, force):
    """Index DDR topics.
    """
    publish.topics(hosts=hosts, report=report, dryrun=dryrun, force=force)


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
def vocabs(hosts, report, dryrun, force):
    """Index DDR vocabulary facets and terms.
    """
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
    publish.sources(
        hosts=hosts, report=report, dryrun=dryrun, force=force, psms_id=sourceid
    )


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.argument('doctype')
def list(hosts, doctype):
    """List titles for all instances of specified doctype.
    """
    publish.listdocs(hosts, doctype)


@encyc.command()
@click.argument('doctype')
@click.argument('object_id')
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.option('--mediawiki', '-m', is_flag=True, default=False, help='Get from MediaWiki.')
@click.option('--json', '-j', is_flag=True, default=False, help='Return ES record as JSON.')
@click.option('--body/--no-body', default=False, help='Include body text.')
def get(hosts, mediawiki, json, body, doctype, object_id):
    """Get a single record
    """
    js = json
    import json
    data = {}
    if mediawiki:
        status_code,text = publish.Proxy._mw_page_text(object_id)
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
        for key,val in data['parse'].iteritems():
            click.echo('{}: {}'.format(key, val))
    else:
        data = publish.get(doctype, object_id, body)
        if isinstance(data, Exception):
            click.echo(data)
            return
        for key,val in data.iteritems():
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
            for key,val in data.iteritems():
                click.echo('{}: {}'.format(key, val))
            click.echo('description: {}'.format(description))
        elif doctype == 'source':
            click.echo('psms_id: {}'.format(data.pop('psms_id')))
            click.echo('encyclopedia_id: {}'.format(data.pop('encyclopedia_id')))
            click.echo('created: {}'.format(data.pop('created')))
            click.echo('modified: {}'.format(data.pop('modified')))
            keys = sorted([key for key in data.iterkeys()])
            for key in keys:
                click.echo('{}: {}'.format(key, data[key]))
        elif doctype == 'author':
            click.echo('title: {}'.format(data.pop('title')))
            click.echo('url_title: {}'.format(data.pop('url_title')))
            click.echo('title_sort: {}'.format(data.pop('title_sort')))
            for key,val in data.iteritems():
                click.echo('{}: {}'.format(key, val))
            

@encyc.command()
@click.option('--confirm', '-C', is_flag=True,
              help='Yes I really want to delete this index.')
@click.argument('doctype')
@click.argument('object_id')
def delete(confirm, doctype, object_id):
    """Delete a single record from Elasticsearch
    """
    result = publish.delete(doctype, object_id, confirm)
    click.echo(result)


@encyc.command()
@click.argument('path')
@click.argument('title')
def parse(title, path):
    """Loads raw MediaWiki JSON from file, emits parsed HTML.
    
    \b
    Combine with `encyc get`:
    encyc get article "Nisei Progressives" -mbj > /tmp/file.json
    encyc parse /tmp/file.json "Nisei Progressives"
    """
    click.echo(publish.parse(path, title))
