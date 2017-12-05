import click

from encyc import config as settings
from encyc import publish


@click.group()
@click.option('--debug', is_flag=True)
def encyc(debug):
    """encyc - publish MediaWiki content to Elasticsearch; debug Elasticsearch
    
    \b
    Index Management: create, delete, reset
    Publishing:       topics, authors, articles, sources
    Debugging:        config, status, list, get
    
    By default the command uses DOCSTORE_HOSTS and DOCSTORE_INDEX from the config file.  The tool will publish to at least two separate sites (Encyclopedia, Resource Guide), you can use the --hosts and --index options to override these values.
    
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
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
def status(hosts, index):
    """Print status info.
    
    More detail since you asked.
    """
    publish.status(hosts, index)


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
def create(hosts, index):
    """Create new index.
    """
    publish.create_index(hosts, index)


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to delete.')
@click.option('--confirm', is_flag=True,
              help='Yes I really want to delete this index.')
def delete(hosts, index, confirm):
    """Delete index (requires --confirm).
    """
    if confirm:
        publish.delete_index(hosts, index)
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX, help='Elasticsearch index.')
@click.option('--alias', default=settings.DOCSTORE_HOSTS, help='Alias to create.')
@click.option('--delete', is_flag=True, help='Delete specified alias.')
def alias(hosts, index, alias, delete):
    """Manage aliases.
    """
    if delete:
        publish.delete_alias(hosts, index, alias)
    else:
        publish.create_alias(hosts, index, alias)


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to reset.')
@click.option('--confirm', is_flag=True,
              help='Yes I really want to delete this index.')
def reset(hosts, index, confirm):
    """Delete existing index and create new one (requires --confirm).
    """
    if confirm:
        publish.delete_index(hosts, index)
        publish.create_index(hosts, index)
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX, help='Elasticsearch index to create.')
def mappings(hosts, index):
    """Push mappings to the specified index.
    """
    publish.push_mappings(hosts, index)


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
def topics(hosts, index, report, dryrun, force):
    """Index DDR topics.
    """
    publish.topics(hosts=hosts, index=index, report=report, dryrun=dryrun, force=force)


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
def vocabs(hosts, index, report, dryrun, force):
    """Index DDR vocabulary facets and terms.
    """
    publish.vocabs(hosts=hosts, index=index, report=report, dryrun=dryrun, force=force)


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
@click.option('--title', help='Single author to publish.')
def authors(hosts, index, report, dryrun, force, title):
    """Index authors.
    """
    publish.authors(
        hosts=hosts, index=index, report=report, dryrun=dryrun, force=force, title=title
    )


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
@click.option('--title', help='Single article to publish.')
def articles(hosts, index, report, dryrun, force, title):
    """Index articles.
    """
    publish.articles(
        hosts=hosts, index=index, report=report, dryrun=dryrun, force=force, title=title
    )


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
@click.option('--sourceid', help='Single article to publish.')
def sources(hosts, index, report, dryrun, force, sourceid):
    """Index sources.
    """
    publish.sources(
        hosts=hosts, index=index, report=report, dryrun=dryrun, force=force, psms_id=sourceid
    )


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
@click.argument('doctype')
def list(hosts, index, doctype):
    """List titles for all instances of specified doctype.
    """
    publish.listdocs(hosts, index, doctype)


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
@click.argument('doctype')
@click.argument('object_id')
def get(hosts, index, doctype, object_id):
    """Pretty-print a single record
    """
    publish.get(hosts, index, doctype, object_id)


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
