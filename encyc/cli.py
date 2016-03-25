import click

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
def create():
    """Create new index.
    """
    operations.create_index()


@encyc.command()
@click.option('--confirm', is_flag=True,
              help='Yes I really want to delete this index.')
def delete(confirm):
    """Delete index (requires --confirm).
    """
    if confirm:
        operations.delete_index()
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")


@encyc.command()
@click.option('--confirm', is_flag=True,
              help='Yes I really want to delete this index.')
def reset(confirm):
    """Delete existing index and create new one (requires --confirm).
    """
    if confirm:
        operations.delete_index()
        operations.create_index()
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")


@encyc.command()
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
def topics(report, dryrun, force):
    """Index DDR topics.
    """
    operations.topics(report=report, dryrun=dryrun, force=force)


@encyc.command()
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
def authors(report, dryrun, force):
    """Index authors.
    """
    operations.authors(report=report, dryrun=dryrun, force=force)


@encyc.command()
@click.option('--report', is_flag=True,
              help='Report number of records existing, to be indexed/updated.')
@click.option('--dryrun', is_flag=True,
              help='perform a trial run with no changes made')
@click.option('--force', is_flag=True,
              help='Forcibly update records whether they need it or not.')
def articles(report, dryrun, force):
    """Index articles.
    """
    operations.articles(report=report, dryrun=dryrun, force=force)
