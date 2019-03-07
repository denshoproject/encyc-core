import logging
logger = logging.getLogger(__name__)
import requests

from encyc import config

TIMEOUT = float(config.MEDIAWIKI_API_TIMEOUT)


def get(url, timeout=TIMEOUT, headers={}, data={}, cookies={}, htuser=config.MEDIAWIKI_API_HTUSER, htpass=config.MEDIAWIKI_API_HTPASS):
    """Thin wrapper around requests.get that adds HTTP Basic auth.
    
    HTTP Basic auth required when accessing editors' wiki from outside the LAN.
    """
    logger.debug('GET %s' % url)
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

def post(url, timeout=TIMEOUT, headers={}, data={}, cookies={}, htuser=config.MEDIAWIKI_API_HTUSER, htpass=config.MEDIAWIKI_API_HTPASS):
    """Thin wrapper around requests.post that adds HTTP Basic auth.
    """
    logger.debug('POST %s' % url)
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
