from .indices import Index, Indexer, ModelIndexer, registry  # NOQA
from .helpers import query, parse, index, model_indices, multisearch  # NOQA
from .utils import autodiscover  # NOQA
from .schema import Document  # NOQA
import exceptions  # NOQA

default_app_config = 'springy.apps.SpringyAppConfig'
