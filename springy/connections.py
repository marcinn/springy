from elasticsearch_dsl import connections


def get_connection_for_doctype(doctype, using=None):
    return connections.connections.get_connection(using or 'default')
