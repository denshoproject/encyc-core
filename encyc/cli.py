import click

from encyc import config
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
    click.echo('Debug mode is %s' % ('on' if debug else 'off'))


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
def mappings(hosts):
    """Get mappings.
    """
    publish.mappings(hosts)


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
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.argument('doctype')
@click.argument('object_id')
def get(hosts, doctype, object_id):
    """Pretty-print a single record
    """
    publish.get(hosts, doctype, object_id)


@encyc.command()
@click.option('--hosts', default=DOCSTORE_HOST, help='Elasticsearch hosts.')
@click.argument('doctype')
@click.argument('object_id')
def delete(hosts, doctype, object_id):
    """Delete a single record
    """
    publish.delete(hosts, doctype, object_id)


@encyc.command()
@click.argument('title')
@click.argument('path')
def _json(title, path):
    """Get page text from MediaWiki, dump to file.
    """
    publish._dumpjson(title, path)

@encyc.command()
@click.argument('title')
@click.argument('path')
def _parse(title, path):
    """Load page json from file, generate Page, save HTML to file.
    """
    publish._parse(title, path)
