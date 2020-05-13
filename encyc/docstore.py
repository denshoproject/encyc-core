"""
example walkthrough:
------------------------------------------------------------------------

from encyc import docstore
d = docstore.Docstore()

# Post an object and its child objects.
d.post('/var/www/media/ddr/ddr-densho-10', recursive=True)

# Post vocabularies (used for topics, facility fields)
d.post_vocabs(docstore.VOCABS_URL)

# Narrators metadata
d.narrators('/opt/ddr-local/densho-vocab/api/0.2/narrators.json')

# Delete a collection
d.delete(os.path.basename(PATH), recursive=True)

------------------------------------------------------------------------
"""

import json
import logging
logger = logging.getLogger(__name__)
import os

from elasticsearch import Elasticsearch, TransportError
from elasticsearch.client import SnapshotClient
import elasticsearch_dsl

from encyc import config
from encyc import fileio
from encyc.repo_models import ELASTICSEARCH_CLASSES
from encyc.repo_models import ELASTICSEARCH_CLASSES_BY_MODEL
from encyc.repo_models import MODEL_REPO_MODELS

INDEX_PREFIX = 'encyc'

MAX_SIZE = 10000
DEFAULT_PAGE_SIZE = 20

SUCCESS_STATUSES = [200, 201]

def load_json(path):
    try:
        data = json.loads(fileio.read_text(path))
    except json.errors.JSONDecodeError:
        raise Exception('simplejson.errors.JSONDecodeError reading %s' % path)
    return data


class Docstore():

    def __init__(self, hosts=config.DOCSTORE_HOST, connection=None):
        self.hosts = hosts
        if connection:
            self.es = connection
        else:
            self.es = Elasticsearch(hosts, timeout=config.DOCSTORE_TIMEOUT)
    
    def index_name(self, model):
        return '{}{}'.format(INDEX_PREFIX, model)
    
    def __repr__(self):
        return "<%s.%s %s:%s*>" % (
            self.__module__, self.__class__.__name__, self.hosts, INDEX_PREFIX
        )
    
    def print_configs(self):
        print('CONFIG_FILES:           %s' % config.CONFIG_FILES)
        print('')
        print('DOCSTORE_HOST:          %s' % config.DOCSTORE_HOST)
        print('')
    
    def health(self):
        return self.es.cluster.health()
    
    def start_test(self):
        self.es.cluster.health()
    
    def index_exists(self, indexname):
        """
        """
        return self.es.indices.exists(index=indexname)
    
    def status(self):
        """Returns status information from the Elasticsearch cluster.
        
        >>> docstore.Docstore().status()
        {
            u'indices': {
                u'ddrpublic-dev': {
                    u'total': {
                        u'store': {
                            u'size_in_bytes': 4438191,
                            u'throttle_time_in_millis': 0
                        },
                        u'docs': {
                            u'max_doc': 2664,
                            u'num_docs': 2504,
                            u'deleted_docs': 160
                        },
                        ...
                    },
                    ...
                }
            },
            ...
        }
        """
        return self.es.indices.stats()
    
    def index_names(self):
        """Returns list of index names
        """
        return [name for name in self.status()['indices'].keys()]
    
    def create_indices(self):
        """Create indices for each model defined in encyc/models/elastic.py
        """
        statuses = []
        for i in ELASTICSEARCH_CLASSES['all']:
            status = self.create_index(
                self.index_name(i['doctype']),
                i['class']
            )
            statuses.append(status)
        return statuses
    
    def create_index(self, indexname, dsl_class):
        """Creates the specified index if it does not already exist.
        
        Uses elasticsearch-dsl classes defined in ddr-defs/repo_models/elastic.py
        
        @param indexname: str
        @param dsl_class: elasticsearch_dsl.Document class
        @returns: JSON dict with status codes and responses
        """
        logger.debug('creating index {}'.format(indexname))
        if self.index_exists(indexname):
            status = '{"status":400, "message":"Index exists"}'
            logger.debug('Index exists')
            #print('Index exists')
        else:
            index = elasticsearch_dsl.Index(indexname)
            #print('index {}'.format(index))
            index.aliases(default={})
            #print('registering')
            out = index.document(dsl_class).init(index=indexname, using=self.es)
            if out:
                status = out
            elif self.index_exists(indexname):
                status = {
                    "name": indexname,
                    "present": True,
                }
            #print(status)
            #print('creating index')
        return status
    
    def delete_indices(self):
        """Delete indices for each model defined in ddr-defs/repo_models/elastic.py
        """
        statuses = []
        for i in ELASTICSEARCH_CLASSES['all']:
            status = self.delete_index(
                self.index_name(i['doctype'])
            )
            statuses.append(status)
        return statuses
    
    def delete_index(self, indexname):
        """Delete the specified index.
        
        @returns: JSON dict with status code and response
        """
        logger.debug('deleting index: %s' % indexname)
        if self.index_exists(indexname):
            status = self.es.indices.delete(index=indexname)
        else:
            status = {
                "name": indexname,
                "status": 500,
                "message": "Index does not exist",
            }
        logger.debug(status)
        return status
    
    def model_fields_lists(self):
        pass
    
    def get_mappings(self):
        """Get mappings for ESObjects
        
        @returns: str JSON
        """
        return self.es.indices.get_mapping()
    
    def post_json(self, indexname, document_id, json_text):
        """POST the specified JSON document as-is.
        
        @param indexname: str
        @param document_id: str
        @param json_text: str JSON-formatted string
        @returns: dict Status info.
        """
        logger.debug('post_json(%s, %s)' % (indexname, document_id))
        return self.es.index(
            index=self.index_name(indexname),
            id=document_id,
            body=json_text
        )

    def post(self, document, public_fields=[], additional_fields={}, force=False):
        """Add a new document to an index or update an existing one.
        
        This function can produce ElasticSearch documents in two formats:
        - old-style list-of-dicts used in the DDR JSON files.
        - normal dicts used by ddr-public.
        
        DDR metadata JSON files are structured as a list of fieldname:value dicts.
        This is done so that the fields are always in the same order, making it
        possible to easily see the difference between versions of a file.
        [IMPORTANT: documents MUST contain an 'id' field!]
        
        In ElasticSearch, documents are structured in a normal dict so that faceting
        works properly.
        
        curl -XPUT 'http://localhost:9200/ddr/collection/ddr-testing-141' -d '{ ... }'
        
        @param document: Collection,Entity,File The object to post.
        @param public_fields: list
        @param additional_fields: dict
        @param force: boolean Bypass status and public checks.
        @returns: JSON dict with status code and response
        """
        logger.debug('post(%s, %s)' % (
            document, force
        ))

        if force:
            can_publish = True
            public = False
        else:
            if not parents:
                parents = {
                    oid: oi.object()
                    for oid,oi in _all_parents([document.identifier]).items()
                }
            can_publish = publishable([document.identifier], parents)
            public = True
        if not can_publish:
            return {'status':403, 'response':'object not publishable'}
        
        d = document.to_esobject(public_fields=public_fields, public=public)
        logger.debug('saving')
        results = d.save(
            index=self.index_name(document.identifier.model),
            using=self.es
        )
        logger.debug(str(results))
        return results
     
    def exists(self, model, document_id):
        """
        @param model:
        @param document_id:
        """
        return self.es.exists(
            index=self.index_name(model),
            id=document_id
        )
    
    def get(self, model, document_id, fields=None):
        """Get a single document by its id.
        
        @param model:
        @param document_id:
        @param fields: boolean Only return these fields
        @returns: repo_models.elastic.ESObject or None
        """
        ES_Class = ELASTICSEARCH_CLASSES_BY_MODEL[model]
        return ES_Class.get(
            id=document_id,
            index=self.index_name(model),
            using=self.es,
            ignore=404,
        )

    def count(self, doctypes=[], query={}):
        """Executes a query and returns number of hits.
        
        The "query" arg must be a dict that conforms to the Elasticsearch query DSL.
        See docstore.search_query for more info.
        
        @param doctypes: list Type of object ('collection', 'entity', 'file')
        @param query: dict The search definition using Elasticsearch Query DSL
        @returns raw ElasticSearch query output
        """
        logger.debug('count(doctypes=%s, query=%s' % (doctypes, query))
        if not query:
            raise Exception(
                "Can't do an empty search. Give me something to work with here."
            )
        
        indices = ','.join(
            ['{}{}'.format(INDEX_PREFIX, m) for m in doctypes]
        )
        doctypes = ','.join(doctypes)
        logger.debug(json.dumps(query))
        
        return self.es.count(
            index=indices,
            body=query,
        )
    
    def delete(self, document_id):
        pass

    def search(self, doctypes=[], query={}, sort=[], fields=[], from_=0, size=MAX_SIZE):
        """Executes a query, get a list of zero or more hits.
        
        The "query" arg must be a dict that conforms to the Elasticsearch query DSL.
        See docstore.search_query for more info.
        
        @param doctypes: list Type of object ('collection', 'entity', 'file')
        @param query: dict The search definition using Elasticsearch Query DSL
        @param sort: list of (fieldname,direction) tuples
        @param fields: str
        @param from_: int Index of document from which to start results
        @param size: int Number of results to return
        @returns raw ElasticSearch query output
        """
        logger.debug(
            'search(doctypes=%s, query=%s, sort=%s, fields=%s, from_=%s, size=%s' % (
                doctypes, query, sort, fields, from_, size
        ))
        if not query:
            raise Exception(
                "Can't do an empty search. Give me something to work with here."
            )
        
        indices = ','.join(
            ['{}{}'.format(INDEX_PREFIX, m) for m in doctypes]
        )
        doctypes = ','.join(doctypes)
        logger.debug(json.dumps(query))
        _clean_dict(sort)
        sort_cleaned = _clean_sort(sort)
        fields = ','.join(fields)

        results = self.es.search(
            index=indices,
            body=query,
            #sort=sort_cleaned,  # TODO figure out sorting
            from_=from_,
            size=size,
            #_source_include=fields,  # TODO figure out fields
        )
        return results


def make_index_name(text):
    """Takes input text and generates a legal Elasticsearch index name.
    
    I can't find documentation of what constitutes a legal ES index name,
    but index names must work in URLs so we'll say alnum plus _, ., and -.
    
    @param text
    @returns name
    """
    LEGAL_NONALNUM_CHARS = ['-', '_', '.']
    SEPARATORS = ['/', '\\',]
    name = []
    if text:
        text = os.path.normpath(text)
        for n,char in enumerate(text):
            if char in SEPARATORS:
                char = '-'
            if n and (char.isalnum() or (char in LEGAL_NONALNUM_CHARS)):
                name.append(char.lower())
            elif char.isalnum():
                name.append(char.lower())
    return ''.join(name)

def doctype_fields(es_class):
    """List content fields in DocType subclass (i.e. appear in _source).
    
    TODO move to ddr-cmdln
    """
    return es_class._doc_type.mapping.to_dict()['properties'].keys()

def _clean_dict(data):
    """Remove null or empty fields; ElasticSearch chokes on them.
    
    >>> d = {'a': 'abc', 'b': 'bcd', 'x':'' }
    >>> _clean_dict(d)
    >>> d
    {'a': 'abc', 'b': 'bcd'}
    
    @param data: Standard DDR list-of-dicts data structure.
    """
    if data and isinstance(data, dict):
        for key in data.keys():
            if not data[key]:
                del(data[key])

def _clean_sort( sort ):
    """Take list of [a,b] lists, return comma-separated list of a:b pairs
    
    >>> _clean_sort( 'whatever' )
    >>> _clean_sort( [['a', 'asc'], ['b', 'asc'], 'whatever'] )
    >>> _clean_sort( [['a', 'asc'], ['b', 'asc']] )
    'a:asc,b:asc'
    """
    cleaned = ''
    if sort and isinstance(sort,list):
        all_lists = [1 if isinstance(x, list) else 0 for x in sort]
        if not 0 in all_lists:
            cleaned = ','.join([':'.join(x) for x in sort])
    return cleaned
        
def publishable(page, force=False):
    """Determines which paths represent publishable paths and which do not.
    
    @param page
    @returns list of dicts, e.g. [{'path':'/PATH/TO/OBJECT', 'action':'publish'}]
    """
    pass

def aggs_dict(aggregations):
    """Simplify aggregations data in search results
    
    input
    {
        u'format': {
            u'buckets': [{u'doc_count': 2, u'key': u'ds'}],
            u'doc_count_error_upper_bound': 0,
            u'sum_other_doc_count': 0
        },
        u'rights': {
            u'buckets': [{u'doc_count': 3, u'key': u'cc'}],
            u'doc_count_error_upper_bound': 0, u'sum_other_doc_count': 0
        },
    }
    output
    {
        u'format': {u'ds': 2},
        u'rights': {u'cc': 3},
    }
    """
    return {
        fieldname: {
            bucket['key']: bucket['doc_count']
            for bucket in data['buckets']
        }
        for fieldname,data in aggregations.items()
    }

def search_query(text='', must=[], should=[], mustnot=[], aggs={}):
    pass
