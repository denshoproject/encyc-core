from collections import OrderedDict
from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
import re

from bs4 import BeautifulSoup, SoupStrainer, Comment

from encyc import config
from encyc import http
from encyc.models import helpers

TIMEOUT = float(config.MEDIAWIKI_API_TIMEOUT)


def parse_mediawiki_text(title, html, primary_sources, public=False, printed=False, rg_titles=[]):
    """Parses the body of a MediaWiki page.
    
    @param title: str page title.
    @param html: str HTML contents of page body.
    @param primary_sources: list
    @param public: Boolean
    @param printed: Boolean
    @param rg_titles: list Resource Guide url_titles.
    @returns: html, list of primary sources
    """
    soup = BeautifulSoup(
        html.replace('<p><br />\n</p>',''),
        features='lxml'
    )
    soup = _mark_offsite_encyc_rg_links(soup, title, rg_titles)
    soup = _remove_staticpage_titles(soup)
    soup = _remove_comments(soup)
    soup = _remove_edit_links(soup)
    soup = _wrap_sections(soup)
    soup = _rewrite_newpage_links(soup)
    soup = _rewrite_prevnext_links(soup)
    soup = remove_status_markers(soup)
    if not printed:
        soup = _add_top_links(soup)
    soup = _remove_divs(
        soup,
        selectors=config.HIDDEN_TAGS.get([]),
        comments=config.HIDDEN_TAG_COMMENTS
    )
    soup = _remove_nonrg_divs(soup)
    soup = _remove_primary_sources(soup, primary_sources)
    html = unicode(soup)
    html = _rewrite_mediawiki_urls(html)
    html = _rm_tags(html)
    return html

def _remove_staticpage_titles(soup):
    """strip extra <h1> on "static" pages
    
    Called by parse_mediawiki_text.
    "Static" pages will have an extra <h1> in the page body.
    This is extracted by parse_mediawiki_title so now we need
    to remove it.
    
    @param soup: BeautifulSoup object
    @returns: soup
    """
    h1s = soup.find_all('h1')
    if h1s:
        for h1 in soup.find_all('h1'):
            h1.decompose()
    return soup

def _remove_comments(soup):
    """TODO Removes MediaWiki comments from page text
    
    Called by parse_mediawiki_text.
    
    @param soup: BeautifulSoup object
    @returns: soup
    """
    #def iscomment(tag):
    #    return isinstance(text, Comment)
    #comments = soup.findAll(iscomment)
	#[comment.extract() for comment in comments]
    return soup

def _remove_edit_links(soup):
    """Removes [edit] spans (ex: <span class="editsection">)
    
    Called by parse_mediawiki_text.
    Security precaution: we don't want people to be able to edit,
    or to find edit links.
    
    @param soup: BeautifulSoup object
    @returns: soup
    """
    for e in soup.find_all('span', attrs={'class':'mw-editsection'}):
        e.decompose()
    return soup

def _wrap_sections(soup):
    """Wraps each <h2> and cluster of <p>s in a <section> tag.
    
    Called by parse_mediawiki_text.
    Makes it possible to make certain sections collapsable.
    The thing that makes this complicated is that with BeautifulSoup
    you can't just drop tags into a <div>.  You have to 
    
    @param soup: BeautifulSoup object
    @returns: soup
    """
    HEADERS = ['h2','h3','h4']
    for s in soup.find_all('span', 'mw-headline'):
        # get header tags
        h = s.parent
        h_id = h.find('span')['id']
        # extract the rest of the section from soup
        siblings = []
        for sibling in h.next_siblings:
            if hasattr(sibling, 'name') and sibling.name in HEADERS:
                break
            siblings.append(sibling)
        [sibling.extract() for sibling in siblings]
        # wrap h in a <div>
        div = soup.new_tag('div')
        div['class'] = 'section'
        div['id'] = h_id
        h = h.wrap(div)
        # append section contents into <div>
        div2 = soup.new_tag('div')
        div2['class'] = 'section_content'
        div2.contents = siblings
        h.append(div2)
    return soup

def _rewrite_newpage_links(soup):
    """Rewrites new-page links
    
    Called by parse_mediawiki_text.
    ex: http://.../mediawiki/index.php?title=Nisei&amp;action=edit&amp;redlink=1
    
    @param soup: BeautifulSoup object
    @returns: soup
    """
    for a in soup.find_all('a', href=re.compile('action=edit')):
        a['href'] = a['href'].replace('?title=', '/')
        a['href'] = a['href'].replace('&action=edit', '')
        a['href'] = a['href'].replace('&redlink=1', '')
    return soup

def _rewrite_prevnext_links(soup):
    """Rewrites previous/next links
    
    Called by parse_mediawiki_text.
    ex: http://.../mediawiki/index.php?title=Category:Pages_Needing_Primary_Sources&pagefrom=Mary+Oyama+Mittwer
    
    @param soup: BeautifulSoup object
    @returns: soup
    """
    for a in soup.find_all('a', href=re.compile('pagefrom=')):
        a['href'] = a['href'].replace('?title=', '/')
        a['href'] = a['href'].replace('&pagefrom=', '?pagefrom=')
    for a in soup.find_all('a', href=re.compile('pageuntil=')):
        a['href'] = a['href'].replace('?title=', '/')
        a['href'] = a['href'].replace('&pageuntil=', '?pageuntil=')
    return soup

def __href_title(href, base):
    """Extract title from href
    """
    # can't just replace all slashes bc titles can include slashes
    if href[-1] == '/':
        href = href[:-1]
    href = href.replace(base, '')
    if href[0] == '/':
        href = href[1:]
    return href

def __mark_tag(tag, attr, value):
    """Add specified attr to tag
    """
    if not tag.get(attr, []):
        tag[attr] = []
    tag[attr].append(value)

def __rm_tag(tag, attr, value):
    """Remove specified attr from tag
    """
    orig_attrs = tag.attrs.get(attr, [])
    tag.attrs[attr] = [a for a in orig_attrs if a != value]

def _mark_offsite_encyc_rg_links(soup, title, rg_titles=[]):
    """Add class markers to offsite, Resource Guide, and non-RG links
    
    @param soup: BeautifulSoup object containing page
    @param title: str Page.url_title
    @param rg_titles: list Resource Guide url_titles.
    """
    for a in soup.find_all("a"):
        #print(a)
        
        __rm_tag(a, 'class', 'offsite')
        __rm_tag(a, 'class', 'encyc')
        __rm_tag(a, 'class', 'rg')
        __rm_tag(a, 'class', 'notrg')
        
        a_title = __href_title(a['href'], config.ENCYCRG_ARTICLE_BASE)
        if 'http' in a_title:
            a_title = ''
        a_title_with_spaces = a_title.replace('_', ' ')
        #print('a_title        "%s"' % a_title)
        #print('a_title_spaces "%s"' % a_title_with_spaces)
        
        # ignore page nav and image links
        if (a['href'][0] == '#') or ('File' in a['href']):
            #print('   PASS')
            pass
        
        # offsite
        #elif url.netloc and (url.netloc not in [config.ENCYCRG_ALLOWED_HOSTS]):
        elif ('http:' in a['href']) or ('https:' in a['href']):
            #print('OFFSITE %s' % a['href'])
            __mark_tag(a, 'class', 'offsite')
        
        # resource guide
        elif a_title and( (a_title in rg_titles) or (a_title_with_spaces in rg_titles)):
            #print('     RG %s' % a['href'])
            __mark_tag(a, 'class', 'encyc')
            __mark_tag(a, 'class', 'rg')
        
        # encyc
        else:
            #print('  ENCYC %s' % a['href'])
            __mark_tag(a, 'class', 'encyc')
            __mark_tag(a, 'class', 'notrg')
        
        # Previous iterations of this function rewrote links to the main
        # encyclopedia ('encyc' links) with the encycfront domain, adding
        # the protocol ('http://') and domain.  When the function was run
        # subsequently, these links were understood by the function as offsite
        # links, the markers were removed, and subsequent passes would fail
        # to mark links properly.
        # This function now marks links as rg/notrg but does not modify the
        # href attribute.  It is the consuming app's (e.g. encycrg) job to
        # rewrite the links.
    
    return soup

def remove_status_markers(soup):
    """Remove the "Published", "Needs Primary Sources" tables.
    
    Called by parse_mediawiki_text.
    
    @param soup: BeautifulSoup object
    @returns: soup
    """
    for d in soup.find_all('div', attrs={'class':'alert'}):
        if 'published' in d['class']:
            d.decompose()
    return soup
    
def _add_top_links(soup):
    """Adds ^top links at the end of page sections.
    
    Called by parse_mediawiki_text.
    
    @param soup: BeautifulSoup object
    @returns: soup
    """
    import copy
    TOPLINK_TEMPLATE = '<div class="toplink"><a href="#top"><i class="icon-chevron-up"></i> Top</a></div>'
    toplink = BeautifulSoup(
        TOPLINK_TEMPLATE,
        parse_only=SoupStrainer('div', attrs={'class':'toplink'}),
        features='lxml'
    )
    n = 0
    for h in soup.find_all('h2'):
        if n > 1:
            h.insert_before(copy.copy(toplink))
        n = n + 1
    soup.append(copy.copy(toplink))
    return soup

def _remove_primary_sources(soup, sources):
    """Remove primary sources from the MediaWiki page entirely.
    
    Called by parse_mediawiki_text.
    see http://192.168.0.13/redmine/attachments/4/Encyclopedia-PrimarySourceDraftFlow.pdf
    ...and really look at it.  Primary sources are all displayed in sidebar_right.
    
    @param soup: BeautifulSoup object
    @param sources: list
    @returns: soup
    """
    # all the <a><img>s
    contexts = []
    sources_keys = [s['encyclopedia_id'] for s in sources]
    for a in soup.find_all('a', attrs={'class':'image'}):
        encyclopedia_id = helpers.extract_encyclopedia_id(a.img['src'])
        href = None
        if encyclopedia_id and (encyclopedia_id in sources_keys):
            a.decompose()
    return soup

def _remove_divs(soup, selectors=[], comments=True, separator="="):
    """strip specified divs from soup
    
    Designed to remove "rgdatabox-CoreDisplay" databox from the main public encyclopedia.
    
    @param soup: BeautifulSoup object
    @param selectors: list of "attrib=selector" strings
    @param comments: boolean
    @param selector: str
    @returns: soup
    """
    for selector in selectors:
        attr,val = selector.split(separator)
        tags = soup.find_all(attrs={attr:val})
        for tag in tags:
            if comments:
                tag.replace_with(
                    Comment('"%s" removed' % (val))
                )
            else:
                tag.decompose()
    return soup

def _remove_nonrg_divs(soup):
    """Removes divs inserted by the {{ publish-rgonly }} tag/template.
    TODO this should be part of _remove_divs
    """
    for tag in soup.find_all('div', class_='nopublish-encycfront'):
        tag.decompose()
    return soup

def _rewrite_mediawiki_urls(html):
    """Removes /mediawiki/index.php stub from URLs
    
    Called by parse_mediawiki_text.
    
    @param html: str
    @returns: html
    """
    PATTERNS = [
        '/mediawiki/index.php',
        '/mediawiki',
    ]
    for pattern in PATTERNS:
        html = re.sub(pattern, '', html)
    return html

def _rm_tags(html, tags=['html', 'body']):
    """Remove simple tags (e.g. no attributes)from HTML.
    """
    for tag in tags:
        html = html.replace('<%s>' % tag, '').replace('</%s>' % tag, '')
    return html

def extract_databoxes(body, databox_divs_namespaces):
    """Find the hidden databoxes, extract data. 
    
    Databox data is returned as an OrderedDict to preserve field sequence.
    
    <div id="databox-Books" style="display:none;">
    <p>Title:A Bridge Between Us;
    Author:Julie Shigekuni;
    Illustrator:;
    OrigTitle:;
    </p>
    </div>
    
    {
        'databox-books': {
            'title': 'A Bridge Between Us',
            'author': 'Julie Shigekuni',
            'illustrator': '',
            'origtitle': '',
        }
    }
    
    @param body: str raw HTML
    @param databox_divs_namespaces: dict
    @returns: str,OrderedDict
    """
    soup = BeautifulSoup(body, "lxml")
    databoxes = {}
    for div_id in databox_divs_namespaces.keys():
        data = OrderedDict()
        tag = soup.find(id=div_id)
        if tag:
            # BeautifulSoup returns tag contents as a list.
            # The list is composed of strings (stretches of text) and Tag objects,
            # which are any contents that have HTML tags e.g. "<i>title</i>".
            # We just want a big string, so convert all Tags to strings
            # and join everything together into a big string
            itemparts = ''.join([
                unicode(item)
                for item in tag.p.contents
            ])
            # split into key/value pairs and populate the OrderedDict
            for item in itemparts.split('\n'):
                item = item.strip()
                if item and (':' in item):
                    # Note: many fields contain colons
                    key,val = item.split(':', 1)
                    if ';' in val:
                        val = [i.strip() for i in val.split(';') if i.strip()]
                    # keys are lowercased
                    data[key.lower()] = val
            databoxes[div_id] = data
    return databoxes

def extract_description(body):
    """Gets just the first paragraph of an article
    
    @param body: str raw HTML
    @returns: str
    """
    soup = BeautifulSoup(body, "lxml")
    for p in soup.find_all('p'):
        if p.text and not (';\n' in p.text):
            return p.text.strip()
    return ''

def not_published_encyc(body):
    soup = BeautifulSoup(body, "lxml")
    for div in soup.find_all('div', attrs={'class':'nopublish-encycfront'}):
        return True
    return False
