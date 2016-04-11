import click

from encyc import config as settings
from encyc import operations


@click.group()
@click.option('--debug', is_flag=True)
def encyc(debug):
    """
    Lots of documentation goes here.
    """
    click.echo('Debug mode is %s' % ('on' if debug else 'off'))


@encyc.command()
def config():
    """Print configuration settings.
    
    More detail since you asked.
    """
    operations.print_configs()


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
def status(hosts, index):
    """Print status info.
    
    More detail since you asked.
    """
    operations.status(hosts, index)


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
def create(hosts, index):
    """Create new index.
    """
    operations.create_index(hosts, index)


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
        operations.delete_index(hosts, index)
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")


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
        operations.delete_index(hosts, index)
        operations.create_index(hosts, index)
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")


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
    operations.topics(hosts=hosts, index=index, report=report, dryrun=dryrun, force=force)


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
def authors(hosts, index, report, dryrun, force):
    """Index authors.
    """
    operations.authors(hosts=hosts, index=index, report=report, dryrun=dryrun, force=force)


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
def articles(hosts, index, report, dryrun, force):
    """Index articles.
    """
    operations.articles(hosts=hosts, index=index, report=report, dryrun=dryrun, force=force)


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
@click.argument('doctype')
def list(hosts, index, doctype):
    """List titles for all instances of specified doctype.
    """
    operations.listdocs(hosts, index, doctype)


@encyc.command()
@click.option('--hosts', default=settings.DOCSTORE_HOSTS, help='Elasticsearch hosts.')
@click.option('--index', default=settings.DOCSTORE_INDEX,
              help='Elasticsearch index to create.')
@click.argument('doctype')
@click.argument('object_id')
def get(hosts, index, doctype, object_id):
    """Pretty-print a single record
    """
    operations.get(hosts, index, doctype, object_id)


@encyc.command()
@click.argument('title')
@click.argument('path')
def _json(title, path):
    """Get page text from MediaWiki, dump to file.
    """
    operations._dumpjson(title, path)

@encyc.command()
@click.argument('title')
@click.argument('path')
def _parse(title, path):
    """Load page json from file, generate Page, save HTML to file.
    """
    operations._parse(title, path)
