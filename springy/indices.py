from .connections import get_connection_for_doctype
from .fields import Field
from .utils import model_to_dict, generate_index_name
from .search import IterableSearch
from .schema import model_doctype_factory, Schema
import itertools
import six


class AlreadyRegisteredError(Exception):
    pass


class NotRegisteredError(KeyError):
    pass


class IndicesRegistry(object):
    def __init__(self):
        self._indices = {}

    def register(self, name, cls):
        if not name:
            raise ValueError('Index name can not be empty')

        if name in self._indices:
            raise AlreadyRegisteredError('Index `%s` is already registered' % name)
        self._indices[name] = cls

    def get(self, name):
        try:
            return self._indices[name]
        except KeyError:
            raise NotRegisteredError('Index `%s` is not registered' % name)

    def get_all(self):
        return self._indices.values()


registry = IndicesRegistry()


class IndexOptions(object):
    def __init__(self, meta):
        self.document = getattr(meta, 'document', model_doctype_factory(
            meta.model, meta.index, fields=getattr(meta, 'fields', None),
            exclude=getattr(meta, 'exclude', None)))
        self.optimize_query = getattr(meta, 'optimize_query', False)
        self.index = getattr(meta, 'index', None)
        self.read_consistency = getattr(meta, 'read_consistency', 'quorum')
        self.write_consistency = getattr(meta, 'write_consistency', 'quorum')


class IndexBase(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(IndexBase, cls).__new__

        parents = [b for b in bases if isinstance(b, IndexBase)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, attrs)

        meta = attrs.pop('Meta', None)
        if not meta:
            meta = getattr(new_class, 'Meta', None)

        fields = []

        setattr(new_class, '_meta', IndexOptions(meta))
        setattr(new_class, 'model', getattr(meta, 'model', None))
        setattr(new_class, '_schema', Schema(fields))

        index_name = new_class._meta.index or generate_index_name(new_class)
        registry.register(index_name, new_class)

        return new_class


class Index(six.with_metaclass(IndexBase)):
    def get_query_set(self):
        """
        Return queryset for indexing
        """
        return self.model._default_manager.all()

    def get_search_object(self):
        """
        Return search object instance
        """
        return IterableSearch(index=self._meta.document._doc_type.index)

    def initialize(self, using=None):
        """
        Initialize / update doctype
        """
        self._meta.document.init(using=using)

    def create(self, datadict, meta=None):
        """
        Create document instance based on arguments
        """
        datadict['meta'] = meta or {}
        document = self._meta.document(**datadict)
        document.full_clean()
        return document

    def query(self, *args, **kw):
        """
        Query index
        """
        return self.get_search_object().query(*args, **kw)

    def query_string(self, query):
        """
        Query index with `query_string` and EDisMax parser.
        This is shortcut for `.query('query_string', query='<terms>', use_dis_max=True)`
        """
        return self.get_search_object().parse(query)

    def filter(self, *args, **kw):
        """
        Filter index
        """
        return self.get_search_object().filter(*args, **kw)

    def all(self):
        """
        Return all documents query
        """
        return self.get_search_object()

    def to_doctype(self, obj):
        """
        Convert model instance to ElasticSearch document
        """
        data = model_to_dict(obj)
        meta = {'id': obj.pk}
        return self.create(data, meta=meta)

    def save(self, obj):
        doc = self.to_doctype(obj)
        doc.save()

    def save_many(self, objects, using=None, consistency=None):
        from elasticsearch.helpers import bulk

        def generate_qs():
            qs = iter(objects)
            for item in qs:
                yield self.to_doctype(item)

        doctype_name = self._meta.document._doc_type.name
        index_name = self._meta.document._doc_type.index

        connection = get_connection_for_doctype(self._meta.document, using=using)

        def document_to_action(x):
            data = x.to_dict()
            data['_op_type'] = 'index'
            for key,val in x.meta.to_dict().items():
                data['_%s' % key] = val
            return data

        actions = itertools.imap(document_to_action, generate_qs())
        consistency = consistency or self._meta.write_consistency

        return bulk(connection, actions, index=index_name, doc_type=doctype_name,
                consistency=consistency, refresh=True)[0]

    def update_index(self, using=None, consistency=None):
        self.save_many(self.get_query_set(), using=using,
                consistency=consistency)

    def clear_index(self, using=None, consistency=None):
        from elasticsearch.helpers import scan, bulk
        connection = get_connection_for_doctype(self._meta.document, using=using)
        objs = scan(connection, _source_include=['__non_existent_field__'])
        index_name = self._meta.document._doc_type.index

        def document_to_action(x):
            x['_op_type'] = 'delete'
            return x

        actions = itertools.imap(document_to_action, objs)
        consistency = consistency or self._meta.write_consistency
        bulk(connection, actions, index=index_name, consistency=consistency,
                refresh=True)

    def drop_index(self, using=None):
        from elasticsearch.client.indices import IndicesClient
        connection = get_connection_for_doctype(self._meta.document, using=using)
        return IndicesClient(connection).delete(self._meta.index)

