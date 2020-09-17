from datetime import datetime
import mwclient
import pytest
import requests

from encyc import config
from encyc.models import legacy
from encyc import wiki


NO_MEDIAWIKI_ERR = 'MediaWiki is not available.'

def no_mediawiki():
    """Returns True if cannot contact cluster; use to skip tests
    """
    try:
        print(config.MEDIAWIKI_API)
        r = requests.get(config.MEDIAWIKI_API, timeout=1)
        print(r.status_code)
        if r.status_code == 200:
            return False
    except ConnectionError:
        print('ConnectionError')
        return True
    return True


@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_status_code():
    assert wiki.status_code() == (200, 'OK')

#def test_Page_sortkey():
#    p = legacy.Proxy.page('Brian Niiya')
#    print(p.sortkey())
#    assert 0

@pytest.fixture
def mediawiki_login():
    return wiki.MediaWiki()

# MediaWiki._login

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_MediaWiki_login():
    mw = wiki.MediaWiki()
    assert mw
    assert mw.mw
    #assert isinstance(mw, mwclient.client.Site)

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_MediaWiki_articles_a_z(mediawiki_login):
    mw = mediawiki_login
    titles = mw.articles_a_z()
    for title in titles:
        assert isinstance(title, str)
    # TODO spot-check that titles are in MW?

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_MediaWiki_article_next(mediawiki_login):
    mw = mediawiki_login
    title = mw.article_next('Sanji Abe')
    assert isinstance(title, str)
    assert title == 'Sansei'

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_MediaWiki_article_prev(mediawiki_login):
    mw = mediawiki_login
    title = mw.article_prev('Sanji Abe')
    assert isinstance(title, str)
    assert title == 'Sanga moyu (film)'

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_MediaWiki_author_articles(mediawiki_login):
    mw = mediawiki_login
    titles = mw.author_articles('Brian Niiya')
    for title in titles:
        assert isinstance(title, str)

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_MediaWiki_category_article_types(mediawiki_login):
    mw = mediawiki_login
    titles = mw.category_article_types()
    for title in titles:
        assert isinstance(title, str)
        assert 'Category:' in title

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_MediaWiki_is_article(mediawiki_login):
    mw = mediawiki_login
    assert mw.is_article('Sanji Abe')
    #assert mw.is_article('Brian Niiya') == False

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_MediaWiki_is_author(mediawiki_login):
    mw = mediawiki_login
    assert mw.is_author('Sanji Abe') == False
    assert mw.is_author('Brian Niiya')

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_MediaWiki_published_pages(mediawiki_login):
    mw = mediawiki_login
    pages = mw.published_pages()
    for page in pages:
        assert isinstance(page.get('title',None), str)
        assert isinstance(page.get('timestamp',None), datetime)

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_MediaWiki_published_authors(mediawiki_login):
    mw = mediawiki_login
    pages = mw.published_authors()
    for page in pages:
        assert isinstance(page.get('title',None), str)
