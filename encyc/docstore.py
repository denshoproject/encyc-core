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

from elastictools import docstore
from elastictools.docstore import elasticsearch_dsl

from encyc import config
from encyc import fileio
from encyc.repo_models import ELASTICSEARCH_CLASSES
from encyc.repo_models import ELASTICSEARCH_CLASSES_BY_MODEL
from encyc.repo_models import MODEL_REPO_MODELS


def load_json(path):
    try:
        data = json.loads(fileio.read_text(path))
    except json.errors.JSONDecodeError:
        raise Exception('simplejson.errors.JSONDecodeError reading %s' % path)
    return data


class Docstore(docstore.Docstore):

    def __init__(self, index_prefix, host, settings):
        super(Docstore,self).__init__(index_prefix, host, settings)


class DocstoreManager(docstore.DocstoreManager):

    def __init__(self, index_prefix, host, settings):
        super(DocstoreManager, self).__init__(index_prefix, host, settings)

    def create_indices(self):
        return super(DocstoreManager,self).create_indices(ELASTICSEARCH_CLASSES['all'])

    def delete_indices(self):
        return super(DocstoreManager,self).delete_indices(ELASTICSEARCH_CLASSES['all'])

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

def publishable(page, force=False):
    """Determines which paths represent publishable paths and which do not.
    
    @param page
    @returns list of dicts, e.g. [{'path':'/PATH/TO/OBJECT', 'action':'publish'}]
    """
    pass
