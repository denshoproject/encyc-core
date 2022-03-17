from encyc import docstore
from encyc import config as settings

INDEX_PREFIX = 'encyc'

# see if cluster is available, quit with nice message if not
docstore.Docstore(INDEX_PREFIX, settings.DOCSTORE_HOST, settings).start_test()

# set default hosts and index
DOCSTORE = docstore.Docstore(INDEX_PREFIX, settings.DOCSTORE_HOST, settings)
