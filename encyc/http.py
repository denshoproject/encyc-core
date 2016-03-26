import requests

from encyc import config

TIMEOUT = float(config.MEDIAWIKI_API_TIMEOUT)


def get(url, timeout=TIMEOUT, headers={}, data={}, cookies={}):
    """Thin wrapper around requests.get that adds HTTP Basic auth.
    
    HTTP Basic auth required when accessing editors' wiki from outside the LAN.
    """
    print('GET %s' % url)
    if config.MEDIAWIKI_API_HTUSER and config.MEDIAWIKI_API_HTPASS:
        return requests.get(
            url,
            timeout=timeout, headers=headers, data=data, cookies=cookies,
            auth=(config.MEDIAWIKI_API_HTUSER, config.MEDIAWIKI_API_HTPASS)
        )
    return requests.get(
        url,
        timeout=timeout, headers=headers, data=data, cookies=cookies
    )

def post(url, timeout=TIMEOUT, headers={}, data={}, cookies={}):
    """Thin wrapper around requests.post that adds HTTP Basic auth.
    """
    print('POST %s' % url)
    if config.MEDIAWIKI_API_HTUSER and config.MEDIAWIKI_API_HTPASS:
        return requests.post(
            url,
            timeout=timeout, headers=headers, data=data, cookies=cookies,
            auth=(config.MEDIAWIKI_API_HTUSER, config.MEDIAWIKI_API_HTPASS)
        )
    return requests.post(
        url,
        timeout=timeout, headers=headers, data=data, cookies=cookies
    )
