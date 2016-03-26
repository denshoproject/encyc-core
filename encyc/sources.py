from datetime import datetime
import json

from bs4 import BeautifulSoup

from encyc import config
from encyc import http

TS_FORMAT = '%Y-%m-%d %H:%M:%S'


def source(encyclopedia_id):
    source = None
    url = '%s/primarysource/?encyclopedia_id=%s' % (config.SOURCES_API, encyclopedia_id)
    r = http.get(url, headers={'content-type':'application/json'})
    if r.status_code == 200:
        response = json.loads(r.text)
        if response and (response['meta']['total_count'] == 1):
            source = response['objects'][0]
    return source

def published_sources():
    """Returns list of published Sources.
    """
    sources = []
    url = '%s/primarysource/sitemap/' % config.SOURCES_API
    r = http.get(url, headers={'content-type':'application/json'})
    if r.status_code == 200:
        response = json.loads(r.text)
        sources = [source for source in response['objects']]
    return sources

def replace_source_urls(sources, request):
    """rewrite sources URLs to point to stage domain:port
    
    When viewing the stage site through SonicWall, Android Chrome browser
    won't display media from the outside (e.g. encyclopedia.densho.org).
    """
    fields = ['display','original','streaming_url','thumbnail_lg','thumbnail_sm',]
    old_domain = None
    if hasattr(settings,'STAGE_MEDIA_DOMAIN') and config.STAGE_MEDIA_DOMAIN:
        old_domain = config.STAGE_MEDIA_DOMAIN
    new_domain = request.META['HTTP_HOST']
    if new_domain.find(':') > -1:
        new_domain = new_domain.split(':')[0]
    if old_domain and new_domain:
        for source in sources:
            for f in fields:
                if source.get(f,None):
                    source[f] = source[f].replace(old_domain, new_domain)
    return sources
