from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import os
import re

from bs4 import BeautifulSoup
import requests

from encyc import config
from encyc import http

TIMEOUT = float(config.MEDIAWIKI_API_TIMEOUT)


def columnizer(things, cols):
    columns = []
    collen = round(len(things) / float(cols))
    col = []
    for t in things:
        col.append(t)
        if len(col) > collen:
           columns.append(col)
           col = []
    columns.append(col)
    return columns

def page_data_url(api_url, page_title):
    """URL of MediaWiki API call to get page info.
    
    @parap api_url: str Base URL for MediaWiki API.
    @param page_title: Page title from MediaWiki URL.
    @returns: url
    """
    url = '%s?action=parse&format=json&page=%s'
    return url % (api_url, page_title)

def page_is_published(pagedata):
    """Indicates whether page contains Category:Published template.
    
    @param pagedata: dict Output of API call.
    @returns: Boolean
    """
    published = False
    for category in pagedata['parse']['categories']:
        if category['*'] == 'Published':
            published = True
    return published

def _lastmod_data_url(api_url, page_title):
    """URL of MediaWiki API call to get page revision lastmod.
    
    @parap api_url: str Base URL for MediaWiki API.
    @param page_title: Page title from MediaWiki URL.
    @returns: url
    """
    url = '%s?action=query&format=json&prop=revisions&rvprop=ids|timestamp&titles=%s'
    return url % (api_url, page_title)

def page_lastmod(api_url, page_title):
    """Retrieves timestamp of last modification.
    
    @parap api_url: str Base URL for MediaWiki API.
    @param page_title: Page title from MediaWiki URL.
    @returns: datetime or None
    """
    lastmod = None
    url = _lastmod_data_url(api_url, page_title)
    logging.debug(url)
    r = http.get(url, timeout=TIMEOUT)
    if r.status_code == 200:
        pagedata = r.json()
        pages = list(pagedata['query']['pages'].values())
        ts = pages[0]['revisions'][0]['timestamp']
        lastmod = datetime.strptime(ts, config.MEDIAWIKI_DATETIME_FORMAT_TZ)
    return lastmod

def extract_encyclopedia_id(uri):
    """Attempts to extract a valid Densho encyclopedia ID from the URI
    
    TODO Check if valid encyclopedia ID
    
    @param uri: str
    @returns: eid
    """
    if 'thumb' in uri:
        path,filename = os.path.split(os.path.dirname(uri))
        eid,ext = os.path.splitext(filename)
    else:
        path,filename = os.path.split(uri)
        eid,ext = os.path.splitext(filename)
    return eid
    
def find_primary_sources(api_url, images):
    """Given list of page images, get the ones with encyclopedia IDs.
    
    Called by parse_mediawiki_text.
    
    @param api_url: SOURCES_URL
    @param images: list
    @returns: list of sources
    """
    logging.debug('find_primary_sources(%s, %s)' % (api_url, images))
    logging.debug('looking for %s' % len(images))    
    sources = []
    eids = []
    # anything that might be an encyclopedia_id
    for img in images:
        encyclopedia_id = extract_encyclopedia_id(img)
        if encyclopedia_id:
            eids.append(encyclopedia_id)
    # get sources via sources API
    if eids:
        url = '%s/sources/%s' % (api_url, ','.join(eids))
        r = requests.get(url)
        if r.status_code == 200:
            sources = json.loads(r.text)
    logging.debug('retrieved %s' % len(sources))
    return sources

def find_databoxcamps_coordinates(text):
    """Given the raw wikitext, search for coordinates with Databox-Camps.
    
    <div id="databox-Camps">
    <p>
    SoSUID: w-tule;
    DenshoName: Tule Lake;
    USGName: Tule Lake Relocation Center;
    ...
    GISLat: 41.8833;    <<<
    GISLng: -121.3667;  <<<
    GISTGNId: 2012922;
    ...
    </p>
    </div>

    NOTE: We have some major assumptions here:
    - That there will be only one lng/lat pair in the Databox-Camps.
    - That the lng/lat pair will appear within the Databox-Camps.
    
    @param text: str HTML
    @returns: list of coordinate tuples (lng,lat)
    """
    coordinates = []
    if text.find('databox-Camps') > -1:
        lng = None; lat = None;
        for l in re.findall(re.compile('GISLo*ng: (-*[0-9]+.[0-9]+)'), text):
            lng = float(l)
        for l in re.findall(re.compile('GISLat: (-*[0-9]+.[0-9]+)'), text):
            lat = float(l)
        if lng and lat:
            coordinates = (lng,lat)
    return coordinates

def find_author_info(text):
    """Given raw HTML, extract author display and citation formats.
    
    Example 1:
    <div id="authorByline">
      <b>
        Authored by
        <a href="/Tom_Coffman" title="Tom Coffman">Tom Coffman</a>
      </b>
    </div>
    <div id="citationAuthor" style="display:none;">
      Coffman, Tom
    </div>
    
    Example 2:
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
    
    @param text: str HTML
    @returns: dict of authors
    """
    authors = {'display':[], 'parsed':[],}
    soup = BeautifulSoup(
        text.replace('<p><br />\n</p>',''),
        features='lxml'
    )
    for byline in soup.find_all('div', id='authorByline'):
        for a in byline.find_all('a'):
            if hasattr(a,'contents') and a.contents:
                authors['display'].append(a.contents[0])
    for citation in soup.find_all('div', id='citationAuthor'):
        if hasattr(citation,'contents') and citation.contents:
            names = []
            for n in citation.contents[0].split(';'):
                if 'and' in n:
                    for name in n.split('and'):
                        names.append(name.strip())
                else:
                    names.append(n)
            for n in names:
                try:
                    surname,givenname = n.strip().split(',')
                    name = [surname.strip(), givenname.strip()]
                except:
                    name = [n,]
                    logging.error(n)
                    logging.error('mediawiki.find_author_info')
                    logging.error('ValueError: too many values to unpack')
                authors['parsed'].append(name)
    return authors
