from bs4 import BeautifulSoup
from deepdiff import DeepDiff
import pytest

from encyc.models import wikipage


# helpers --------------------------------------------------------------

def _mksoup(html):
    soup =  BeautifulSoup(
        html.replace('<p><br />\n</p>',''),
        features='html.parser'
    )
    if soup.html and soup.html.body:
        soup.html.body.unwrap()
    if soup.html:
        soup.html.unwrap()
    return soup

def rm_whitespace(html):
    lines = [line.strip() for line in html.splitlines()]
    text = ''.join(lines)  # join without newlines
    return text


# tests ----------------------------------------------------------------

# parse_mediawiki_text

RM_STATICPAGE_TITLES_in0 = """
<p>BEFORE</p>
<h1>HEADER</h1>
<p>AFTER</p>
"""

RM_STATICPAGE_TITLES_out0 = """
<p>BEFORE</p>

<p>AFTER</p>
"""

def test_remove_staticpage_titles():
    out = rm_whitespace(str(
        wikipage._remove_staticpage_titles(_mksoup(RM_STATICPAGE_TITLES_in0))
    ))
    expected = rm_whitespace(str(_mksoup(
        RM_STATICPAGE_TITLES_out0
    )))
    print('"%s"' % out)
    print('"%s"' % expected)
    assert out == expected

def test_remove_comments():
    # doesn't do anything right now
    pass

RM_EDIT_LINKS_in0 = """
<p>BEFORE</p>
<h2>HEADER<span class="mw-editsection">...</span></h2>
<p>AFTER</p>
"""

RM_EDIT_LINKS_out0 = """
<p>BEFORE</p>
<h2>HEADER</h2>
<p>AFTER</p>
"""

def test_remove_edit_links():
    out = wikipage._remove_edit_links(_mksoup(RM_EDIT_LINKS_in0))
    assert out == _mksoup(RM_EDIT_LINKS_out0)

WRAP_SECTIONS_in0 = """
<p>BEFORE</p>
<h2><span id="0" class="mw-headline">HEADER0</span></h2>
<p>blah blah blah</p>
<p>blah blah blah</p>
<h2><span id="1" class="mw-headline">HEADER1</span></h2>
<p>blah blah blah</p>
<p>blah blah blah</p>
<h2><span id="2" class="mw-headline">HEADER2</span></h2>
<p>blah blah blah</p>
<p>blah blah blah</p>
<h2>HEADER2</h2>
<p>AFTER</p>
"""

WRAP_SECTIONS_out0 = """
<p>BEFORE</p>
<div class="section" id="0">
<h2><span class="mw-headline" id="0">HEADER0</span></h2>
<div class="section_content">
<p>blah blah blah</p>
<p>blah blah blah</p>
</div>
</div>
<div class="section" id="1">
<h2><span class="mw-headline" id="1">HEADER1</span></h2>
<div class="section_content">
<p>blah blah blah</p>
<p>blah blah blah</p>
</div>
</div>
<div class="section" id="2">
<h2><span class="mw-headline" id="2">HEADER2</span></h2>
<div class="section_content">
<p>blah blah blah</p>
<p>blah blah blah</p>
</div>
</div>
<h2>HEADER2</h2>
<p>AFTER</p>
"""

def test_wrap_sections():
    soup = _mksoup(WRAP_SECTIONS_in0)
    out = rm_whitespace(str(
        wikipage._wrap_sections(soup)
    ))
    expected = rm_whitespace(str(_mksoup(
        WRAP_SECTIONS_out0
    )))
    print('"%s"' % out)
    print('"%s"' % expected)
    assert out == expected

def test_rewrite_newpage_links():
    in0 = '<a href="http://.../mediawiki/index.php?title=Nisei&amp;action=edit&amp;redlink=1">LINK</a>'
    out0 = '<a href="http://.../mediawiki/index.php/Nisei">LINK</a>'
    soup = _mksoup(in0)
    out = wikipage._rewrite_newpage_links(soup)
    expected = _mksoup(out0)
    assert out == expected

def test_rewrite_prevnext_links():
    in0 = '<a href="http://.../mediawiki/index.php?title=Test_Page&pagefrom=Another+Page">LINK</a>'
    in1 = '<a href="http://.../mediawiki/index.php?title=Test_Page&pageuntil=Another+Page">LINK</a>'
    expected0 = '<a href="http://.../mediawiki/index.php/Test_Page?pagefrom=Another+Page">LINK</a>'
    expected1 = '<a href="http://.../mediawiki/index.php/Test_Page?pageuntil=Another+Page">LINK</a>'
    out0 = wikipage._rewrite_prevnext_links(_mksoup(in0))
    out1 = wikipage._rewrite_prevnext_links(_mksoup(in1))
    assert out0 == _mksoup(expected0)
    assert out1 == _mksoup(expected1)

#def test_href_title():
#def test_mark_tag():
#def test_rm_tag():
#def test_mark_offsite_encyc_rg_links():


RM_STATUS_MARKERS_in0 = """<p>BEFORE</p>
<div class="alert alert-success published">
<p>This page is complete and will be published to the production Encyclopedia.</p>
</div>
<p>AFTER</p>"""

RM_STATUS_MARKERS_out0 = """<p>BEFORE</p>

<p>AFTER</p>"""

def test_remove_status_markers():
    soup = _mksoup(RM_STATUS_MARKERS_in0)
    out = rm_whitespace(str(
        wikipage.remove_status_markers(soup)
    ))
    expected = rm_whitespace(str(_mksoup(
        RM_STATUS_MARKERS_out0
    )))
    print('"%s"' % out)
    print('"%s"' % expected)
    assert out == expected

ADD_TOP_LINKS_in0 = """
<p>PARAGRAPH0</p>
<h2>HEADER1</h2>
<p>PARAGRAPH1</p>
<h2>HEADER2</h2>
<p>PARAGRAPH2</p>
<h2>HEADER3</h2>
<p>PARAGRAPH3</p>
"""
ADD_TOP_LINKS_out0 = """<p>PARAGRAPH0</p>
<h2>HEADER1</h2>
<p>PARAGRAPH1</p>
<h2>HEADER2</h2>
<p>PARAGRAPH2</p>
<div class="toplink"><a href="#top"><i class="icon-chevron-up"></i> Top</a></div><h2>HEADER3</h2>
<p>PARAGRAPH3</p><div class="toplink"><a href="#top"><i class="icon-chevron-up"></i> Top</a></div>"""

#def test_add_top_links():
#    out = str(
#        wikipage._add_top_links(_mksoup(ADD_TOP_LINKS_in0))
#    )
#    expected = str(_mksoup(
#        ADD_TOP_LINKS_out0
#    ))
#    assert out == expected

RM_PRIMARY_SOURCES_in0 = """<p>BEFORE</p>
<div><a href="/mediawiki/File:en-denshopd-i37-00239-1.jpg" class="image"><img src="/mediawiki/images/thumb/a/a1/en-denshopd-i37-00239-1.jpg/200px-en-denshopd-i37-00239-1.jpg"  /></a></div>
<div><a href="/mediawiki/File:en-denshovh-ffrank-01-0025-1.jpg" class="image"><img src="/mediawiki/images/thumb/8/86/en-denshovh-ffrank-01-0025-1.jpg/200px-en-denshovh-ffrank-01-0025-1.jpg" /></a></div>
<p>AFTER</p>"""

RM_PRIMARY_SOURCES_out0 = """<p>BEFORE</p>
<div></div>
<div></div>
<p>AFTER</p>"""

def test_remove_primary_sources():
    sources0 = [
        {'encyclopedia_id': 'en-denshopd-i37-00239-1'},
        {'encyclopedia_id': 'en-denshovh-ffrank-01-0025-1'},
    ]
    soup0 = _mksoup(RM_PRIMARY_SOURCES_in0)
    soup0 = wikipage._remove_primary_sources(soup0, sources0)
    out = rm_whitespace(str(
        wikipage._rm_tags(str(soup0))
    ))
    expected = rm_whitespace(str(_mksoup(
        RM_PRIMARY_SOURCES_out0
    )))
    assert out == expected

#def test_remove_divs():
#def test_remove_nonrg_divs():

def test_rewrite_mediawiki_urls():
    in0 = """<a href="http://example.com/mediawiki/index.php/Page Title">Page Title</a>"""
    in1 = """<a href="http://example.com/mediawiki/Page Title">Page Title</a>"""
    in2 = """<a href="http://example.com/Page Title">Page Title</a>"""
    out = """<a href="http://example.com/Page Title">Page Title</a>"""
    assert wikipage._rewrite_mediawiki_urls(in0) == out
    assert wikipage._rewrite_mediawiki_urls(in1) == out
    assert wikipage._rewrite_mediawiki_urls(in2) == out

def test_rm_tags():
    in0 = """<html><body><p>Some text here.</p></body></html>"""
    out0 = """<p>Some text here.</p>"""
    assert wikipage._rm_tags(in0) == out0

#def test_extract_databoxes():
#def test_extract_description():
#def test_not_published_encyc():
