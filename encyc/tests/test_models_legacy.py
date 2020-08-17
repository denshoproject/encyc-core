from datetime import datetime
import json

import mwclient
import pytest
import requests

from encyc import config
from encyc.models import legacy
from encyc import wiki


NO_MEDIAWIKI_ERR = 'MediaWiki is not available.'
NO_PSMS_ERR = 'encycpsms is not available.'
NO_ELASTICSEARCH_ERR = 'Elasticsearch is not available.'

def no_mediawiki():
    """Returns True if cannot contact cluster; use to skip tests
    """
    try:
        print(config.MEDIAWIKI_API)
        r = requests.get(config.MEDIAWIKI_API, timeout=3)
        print(r.status_code)
        if r.status_code == 200:
            return False
    except ConnectionError:
        print('ConnectionError')
        return True
    return True

def no_psms():
    """Returns True if cannot contact server; use to skip tests
    """
    try:
        print(config.SOURCES_API)
        r = requests.get(config.SOURCES_API, timeout=3)
        print(r.status_code)
        if r.status_code == 200:
            return False
    except ConnectionError:
        print('ConnectionError')
        return True
    return True

@pytest.fixture
def mediawiki_login():
    return wiki.MediaWiki()


def test_make_titlesort():
    assert legacy.make_titlesort('abesanji', 'Sanji Abe') == 'abesanji'
    assert legacy.make_titlesort('Sanji Abe', 'Sanji Abe') == 'sanjiabe'
    assert legacy.make_titlesort('', 'Sanji Abe') == 'sanjiabe'
    assert legacy.make_titlesort('', 'The Title') == 'thetitle'

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_Page_pagedata(mediawiki_login):
    mw = mediawiki_login
    page = legacy.Page.pagedata(mw, 'Sanji Abe')
    assert page
    assert isinstance(page, str)
    data = json.loads(page)
    assert data
    assert isinstance(data, dict)

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_Page_get(mediawiki_login):
    mw = mediawiki_login
    page = legacy.Page.get(mw, 'Sanji Abe')
    assert page
    assert isinstance(page, legacy.Page)

#TODO def test_Page_topics():

#@pytest.mark.skipif(no_PSMS(), reason=NO_PSMS_ERR)
#def test_Source_source():
#    x = legacy.Source.source()

def test_fix_external_url():
    arg,result = 'http://lccn.loc.gov/sn83025333','http://lccn.loc.gov/sn83025333'
    assert legacy.fix_external_url(arg) == result
    arg,result = 'http://ddr.densho.org/ddr-densho-67-19/','http://ddr.densho.org/ddr-densho-67-19/'
    assert legacy.fix_external_url(arg) == result
    arg,result = 'http://ddr.densho.org/ddr/densho/67/19/','http://ddr.densho.org/ddr-densho-67-19/'
    assert legacy.fix_external_url(arg) == result

#def test_Proxy_articles():
#    out = legacy.Proxy.articles()

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_Proxy_authors(mediawiki_login):
    mw = mediawiki_login
    titles = legacy.Proxy.authors(mw)
    assert titles
    assert isinstance(titles, list)
    for title in titles:
        assert isinstance(title, str)

@pytest.mark.skipif(no_mediawiki(), reason=NO_MEDIAWIKI_ERR)
def test_Proxy_articles_lastmod(mediawiki_login):
    mw = mediawiki_login
    pages = legacy.Proxy.articles_lastmod(mw)
    assert pages
    assert isinstance(pages, list)
    for page in pages:
        assert isinstance(page, dict)
        assert isinstance(page['title'], str)
        assert isinstance(page['lastmod'], datetime)

@pytest.mark.skipif(no_psms(), reason=NO_PSMS_ERR)
def test_Proxy_sources_all():
    sources = legacy.Proxy.sources_all()
    assert sources
    assert isinstance(sources, list)
    for source in sources:
        assert isinstance(source, legacy.Source)

#Proxy.citation

#Contents
