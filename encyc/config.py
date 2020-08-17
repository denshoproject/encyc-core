import configparser
import os
import sys

CONFIG_FILES = [
    '/etc/encyc/core.cfg',
    '/etc/encyc/core-local.cfg'
]

class NoConfigError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def read_configs(paths):
    config = configparser.ConfigParser()
    configs_read = config.read(paths)
    if not configs_read:
        raise NoConfigError("Could not read config files: %s" % paths)
    return config

config = read_configs(CONFIG_FILES)

DEBUG = config.getboolean('debug', 'debug')
STAGE = False

#elasticsearch
DOCSTORE_HOST = config.get('elasticsearch','docstore_host')
DOCSTORE_TIMEOUT = int(config.get('elasticsearch','docstore_timeout'))

# mediawiki
MEDIAWIKI_SCHEME = config.get('mediawiki', 'scheme')
MEDIAWIKI_HOST = config.get('mediawiki', 'host')
MEDIAWIKI_USERNAME = config.get('mediawiki', 'username')
MEDIAWIKI_PASSWORD = config.get('mediawiki', 'password')
MEDIAWIKI_HTTP_USERNAME = config.get('mediawiki', 'http_username')
MEDIAWIKI_HTTP_PASSWORD = config.get('mediawiki', 'http_password')
MEDIAWIKI_API = f'{MEDIAWIKI_SCHEME}://{MEDIAWIKI_HOST}/api.php'
MEDIAWIKI_API_TIMEOUT = int(config.get('mediawiki', 'api_timeout'))
try:
    MEDIAWIKI_DATABOXES = {
        keyval.split(':')[0].strip(): keyval.split(':')[1].strip()
        for keyval in config.get('mediawiki', 'databoxes').split(';')
    }
except:
    raise Exception('mediawiki.databox format: "MWDIVID:PREFIX;MWDIVID:PREFIX"')
MEDIAWIKI_HIDDEN_CATEGORIES = config.get('mediawiki', 'hidden_categories').split(',')
MEDIAWIKI_SHOW_UNPUBLISHED = config.getboolean('mediawiki', 'show_unpublished')
MEDIAWIKI_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
MEDIAWIKI_DATETIME_FORMAT_TZ = '%Y-%m-%dT%H:%M:%SZ'


# citations
AUTHORS_DEFAULT = 'Densho Encyclopedia contributors.'

# primary sources / psms
SOURCES_API = config.get('sources', 'api_url')
SOURCES_API_USERNAME = None
SOURCES_API_PASSWORD = None
try:
    SOURCES_API_HTUSER = config.get('sources', 'api_htuser')
except:
    SOURCES_API_HTUSER = None
try:
    SOURCES_API_HTPASS = config.get('sources', 'api_htpass')
except:
    SOURCES_API_HTPASS = None
SOURCES_BASE = config.get('sources', 'local_base')
SOURCES_URL = config.get('sources', 'source_url')
SOURCES_DEST = config.get('sources', 'remote_dest')
SOURCES_MEDIA_URL = config.get('sources', 'media_url')
SOURCES_MEDIA_URL_LOCAL = config.get('sources', 'media_url_local')
SOURCES_MEDIA_BUCKET = config.get('sources', 'media_bucket')
RTMP_STREAMER = config.get('sources', 'rtmp_streamer')

# ddr
DDR_API = config.get('ddr', 'api_url')
DDR_MEDIA_URL = config.get('ddr', 'media_url')
DDR_MEDIA_URL_LOCAL = config.get('ddr', 'media_url_local')
DDR_MEDIA_URL_LOCAL_MARKER = config.get('ddr', 'media_url_local_marker')
DDR_VOCABS_BASE = config.get('ddr', 'vocabs_base')
DDR_VOCABS = config.get('ddr', 'vocabs').split(',')
DDR_TOPICS_SRC_URL = config.get('ddr', 'topics_src_url')
DDR_TOPICS_BASE = config.get('ddr', 'topics_base')

# encycfront
ENCYCFRONT_PROTOCOL = config.get('encycfront', 'protocol')
ENCYCFRONT_DOMAIN = config.get('encycfront', 'domain')
ENCYCFRONT_API_BASE = config.get('encycfront', 'api_base')
ENCYCFRONT_ARTICLE_BASE = config.get('encycfront', 'article_base')
ENCYCFRONT_API = '%s://%s%s' % (ENCYCFRONT_PROTOCOL, ENCYCFRONT_DOMAIN, ENCYCFRONT_API_BASE)

# encycrg
# Used to mark URLs in the Resource Guide.
ENCYCRG_PROTOCOL = config.get('encycrg', 'protocol')
ENCYCRG_DOMAIN = config.get('encycrg', 'domain')
ENCYCRG_ALLOWED_HOSTS = config.get('encycrg', 'allowed_hosts')
ENCYCRG_API_BASE = config.get('encycrg', 'api_base')
ENCYCRG_ARTICLE_BASE = config.get('encycrg', 'article_base')
ENCYCRG_API = '%s://%s%s' % (ENCYCRG_PROTOCOL, ENCYCRG_DOMAIN, ENCYCRG_API_BASE)

#import redis
#CACHE = redis.StrictRedis()
from walrus import Database
db = Database()
CACHE = db.cache()
CACHE_TIMEOUT = 60*15

# Sample core.cfg:
#
#   [hidden:encyc-stage]
#   id=somethingelse
#   [hidden:encyc-production]
#   id=rgdatabox-CoreDisplay;somethingelse
#
def read_hidden_tags(config):
    hidden = {}
    for section in config.sections():
        if 'hidden:' in section:
            index = section.split(':')[1]
            hidden[index] = []
            for attrib,selector in config.items(section):
                for selector in selector.split(';'):
                    combo = '%s=%s' % (attrib, selector)
                    if combo not in hidden[index]:
                        hidden[index].append(combo)
    # As of ES 7 we no longer have separate stage and production indices
    # pick stage or production
    if STAGE:
        for key in hidden.keys():
            if 'stage' in key:
                return hidden[key]
    else:
        for key in hidden.keys():
            if 'production' in key:
                return hidden[key]

# hide tags with the given attrib=selector
HIDDEN_TAGS = read_hidden_tags(config)
# display comment for each hidden tag
HIDDEN_TAG_COMMENTS = True
