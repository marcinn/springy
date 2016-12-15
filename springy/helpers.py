from .search import Search, MultiSearch
from .utils import index_to_string
from .indices import registry


def query(*indices):
    """
    Query specified indices provided as names or Index clasess/instances.
    When omitted the search query will be performed on all indices.

    This helper will instantiate `Search` object to perform further queries.
    """

    indices = map(index_to_string, indices)
    return Search(index=indices)


def parse(query_string):
    return query().parse(query_string)


def multisearch(index_name=None):
    return MultiSearch(index=index(index_name) if index_name else None)


def index(name):
    """
    Shortcut to getting and instantiate index class from registry
    """
    return registry.get(name)


def model_indices(model_class):
    """
    Shortcut to getting registered index instances for specified model
    """

    return map(lambda x: x(), registry.get_for_model(model_class))
