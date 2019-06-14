from bs4 import BeautifulSoup
from deepdiff import DeepDiff
import pytest

from encyc.models import helpers


#def test_columnizer():

def test_page_data_url():
    api_url = 'http://example.com'
    page_title = 'Testing'
    out = 'http://example.com?action=parse&format=json&page=Testing'
    assert helpers.page_data_url(api_url, page_title) == out

def test_page_is_published():
    pagedata0 = {
        'parse': {
            'categories': [
                {u'hidden': u'', u'*': u'Published', u'sortkey': u''},
                {u'*': u'Camps', u'sortkey': u''},
            ]
        }
    }
    pagedata1 = {
        'parse': {
            'categories': [
                {u'*': u'Camps', u'sortkey': u''},
            ]
        }
    }
    assert helpers.page_is_published(pagedata0) == True
    assert helpers.page_is_published(pagedata1) == False

def test_lastmod_data_url():
    api_url = 'http://example.com'
    page_title = 'Testing'
    out = 'http://example.com?action=query&format=json&prop=revisions&rvprop=ids|timestamp&titles=Testing'
    assert helpers._lastmod_data_url(api_url, page_title) == out

#def test_page_lastmod():

def test_extract_encyclopedia_id():
    in0 = 'en-denshopd-i37-00239-1.jpg'
    in1 = '/mediawiki/images/thumb/a/a1/en-denshopd-i37-00239-1.jpg/200px-en-denshopd-i37-00239-1.jpg'
    in2 = 'en-denshovh-ffrank-01-0025-1.jpg'
    in3 = '/mediawiki/images/thumb/8/86/en-denshovh-ffrank-01-0025-1.jpg/200px-en-denshovh-ffrank-01-0025-1.jpg'
    out0 = 'en-denshopd-i37-00239-1'
    out1 = 'en-denshopd-i37-00239-1'
    out2 = 'en-denshovh-ffrank-01-0025-1'
    out3 = 'en-denshovh-ffrank-01-0025-1'
    assert helpers.extract_encyclopedia_id(in0) == out0
    assert helpers.extract_encyclopedia_id(in1) == out1
    assert helpers.extract_encyclopedia_id(in2) == out2
    assert helpers.extract_encyclopedia_id(in3) == out3

#def test_find_primary_sources():

FIND_DATABOXCAMPS_COORDS_in0 = """
Just some random text that contains no coordinates
"""
FIND_DATABOXCAMPS_COORDS_in1 = """
<div id="databox-Camps">
<p>
SoSUID: w-tule;
DenshoName: Tule Lake;
USGName: Tule Lake Relocation Center;
GISLat: 41.8833;
GISLng: -121.3667;
GISTGNId: 2012922;
</p>
</div>
"""

def test_find_databoxcamps_coordinates():
    out0a = (); out0b = []
    out1a = (-121.3667, 41.8833); out1b = [-121.3667, 41.8833]
    # TODO test for multiple coordinates on page
    assert helpers.find_databoxcamps_coordinates(
        FIND_DATABOXCAMPS_COORDS_in0
    ) in [out0a, out0b]
    assert helpers.find_databoxcamps_coordinates(
        FIND_DATABOXCAMPS_COORDS_in1
    ) in [out1a, out1b]

FIND_AUTHOR_INFO_in0 = """
<div id="authorByline">
  <b>
    Authored by
    <a href="/Tom_Coffman" title="Tom Coffman">Tom Coffman</a>
  </b>
</div>
<div id="citationAuthor" style="display:none;">
  Coffman, Tom
</div>
"""
FIND_AUTHOR_INFO_in1 = """
<div id="authorByline">
  <b>
    Authored by
    <a href="/mediawiki/index.php/Jane_L._Scheiber" title="Jane L. Scheiber">Jane L. Scheiber</a>
    and
    <a href="/mediawiki/index.php/Harry_N._Scheiber" title="Harry N. Scheiber">Harry N. Scheiber</a>
  </b>
</div>
<div id="citationAuthor" style="display:none;">
  Scheiber,Jane; Scheiber,Harry
</div>
"""

def test_find_author_info():
    out0 = {
        'display': [u'Tom Coffman'],
        'parsed': [[u'Coffman', u'Tom']]
    }
    out1 = {
        'display': [u'Jane L. Scheiber', u'Harry N. Scheiber'],
        'parsed': [[u'Scheiber', u'Jane'], [u'Scheiber', u'Harry']]
    }
    assert helpers.find_author_info(FIND_AUTHOR_INFO_in0) == out0
    assert helpers.find_author_info(FIND_AUTHOR_INFO_in1) == out1
