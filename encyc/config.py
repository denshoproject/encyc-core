import ConfigParser
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
    config = ConfigParser.ConfigParser()
    configs_read = config.read(paths)
    if not configs_read:
        raise NoConfigError("Could not read config files: %s" % paths)
    return config

config = read_configs(CONFIG_FILES)

DEBUG = config.get('debug', 'debug')
STAGE = False

#elasticsearch
DOCSTORE_HOSTS = []
for node in config.get('elasticsearch', 'hosts').strip().split(','):
    host,port = node.strip().split(':')
    DOCSTORE_HOSTS.append(
        {'host':host, 'port':port}
    )
DOCSTORE_INDEX = config.get('elasticsearch', 'index')

# mediawiki
MEDIAWIKI_API = config.get('mediawiki', 'api_url')
MEDIAWIKI_API_USERNAME = config.get('mediawiki', 'api_username')
MEDIAWIKI_API_PASSWORD = config.get('mediawiki', 'api_password')
try:
    MEDIAWIKI_API_HTUSER = config.get('mediawiki', 'api_htuser')
except:
    MEDIAWIKI_API_HTUSER = None
try:
    MEDIAWIKI_API_HTPASS = config.get('mediawiki', 'api_htpass')
except:
    MEDIAWIKI_API_HTPASS = None
MEDIAWIKI_API_TIMEOUT = config.get('mediawiki', 'api_timeout')
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
ENCYCFRONT_DOMAIN = config.get('encycfront', 'domain')
ENCYCFRONT_API_BASE = config.get('encycfront', 'api_base')
ENCYCFRONT_ARTICLE_BASE = config.get('encycfront', 'article_base')
ENCYCFRONT_API = 'http://%s%s' % (ENCYCFRONT_DOMAIN, ENCYCFRONT_API_BASE)

# encycrg
# Used to mark URLs in the Resource Guide.
ENCYCRG_DOMAIN = config.get('encycrg', 'domain')
ENCYCRG_API_BASE = config.get('encycrg', 'api_base')
ENCYCRG_ARTICLE_BASE = config.get('encycrg', 'article_base')
ENCYCRG_API = 'http://%s%s' % (ENCYCRG_DOMAIN, ENCYCRG_API_BASE)


from rc import Cache
cache = Cache()


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
    return hidden

# hide tags with the given attrib=selector
HIDDEN_TAGS = read_hidden_tags(config)
# display comment for each hidden tag
HIDDEN_TAG_COMMENTS = True
