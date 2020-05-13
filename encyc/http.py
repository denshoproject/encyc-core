import logging
logger = logging.getLogger(__name__)
from urllib.parse import urlparse

import requests

from encyc import config

TIMEOUT = float(config.MEDIAWIKI_API_TIMEOUT)


def get(url, timeout=TIMEOUT, headers={}, data={}, cookies={}):
    """Thin wrapper around requests.get that adds HTTP Basic auth.
    
    HTTP Basic auth required when accessing editors' wiki from outside the LAN.
    """
    logger.debug('GET %s' % url)
    htuser,htpass = htuser_htpass(url)
    if htuser and htpass:
        return requests.get(
            url,
            timeout=timeout, headers=headers, data=data, cookies=cookies,
            auth=(htuser, htpass)
        )
    return requests.get(
        url,
        timeout=timeout, headers=headers, data=data, cookies=cookies
    )

def post(url, timeout=TIMEOUT, headers={}, data={}, cookies={}):
    """Thin wrapper around requests.post that adds HTTP Basic auth.
    """
    logger.debug('POST %s' % url)
    htuser,htpass = htuser_htpass(url)
    if htuser and htpass:
        return requests.post(
            url,
            timeout=timeout, headers=headers, data=data, cookies=cookies,
            auth=(htuser, htpass)
        )
    return requests.post(
        url,
        timeout=timeout, headers=headers, data=data, cookies=cookies
    )


def htuser_htpass(url):
    """Supply username/password for domain if specified.
    
    @param url: str
    @returns: tuple (str,str)
    """
    username = None; password = None
    if urlparse(url).netloc == urlparse(config.MEDIAWIKI_API).netloc:
        username = config.MEDIAWIKI_API_HTUSER
        password = config.MEDIAWIKI_API_HTPASS
    elif urlparse(url).netloc == urlparse(config.SOURCES_API).netloc:
        username = config.SOURCES_API_HTUSER
        password = config.SOURCES_API_HTPASS
    #print('{} -> {},{}'.format(url,username,password))
    return username,password
