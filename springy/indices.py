from collections import defaultdict
import itertools

from elasticsearch_dsl import Index as DSLIndex

from .connections import get_connection_for_doctype, get_connection_for_index
from .fields import Field
from .utils import model_to_dict, generate_index_name
from .search import IterableSearch, MultiSearch
from .schema import model_doctype_factory, doctype_factory, Schema
from .exceptions import DocumentDoesNotExist, FieldDoesNotExist


class AlreadyRegisteredError(Exception):
    pass


class NotRegisteredError(KeyError):
    pass


class IndicesRegistry(object):
    def __init__(self):
        self._indices = {}
        self._indexers = defaultdict(list)
        self._model_indices = defaultdict(list)

    def register(self, name, cls):
        if not name:
            raise ValueError('Index name can not be empty')

        if name in self._indices:
            raise AlreadyRegisteredError(
                    'Index `%s` is already registered' % name)

        index = cls()
        for indexer in self._indexers[name]:
            index.add_indexer(indexer)
        self._indexers[name] = []

        self._indices[name] = index

    def register_indexer(self, index_name, cls):
        if cls in self._indexers[index_name]:
            raise AlreadyRegisteredError(
                    'Indexer `%s` is already registered' % cls)
        else:
            if index_name in self._indices:
                self._indices[index_name].add_indexer(cls)
            else:
                self._indexers[index_name].append(cls)

        if isinstance(cls, ModelIndexer):
            self._model_indices[cls.model].append(index_name)

    def get(self, name):
        try:
            return self._indices[name]
        except KeyError:
            raise NotRegisteredError('Index `%s` is not registered' % name)

    def get_all(self):
        return self._indices.values()

    def get_for_model(self, model):
        return map(self.get, self._model_indices[model])

    def unregister(self, cls):
        to_unregister = []
        for name, idx in self._indices.items():
            if idx == cls:
                to_unregister.append(name)
        if not to_unregister:
            raise NotRegisteredError('Index class `%s` is not registered')

        self._model_indices[cls.model].remove(cls)

        for name in to_unregister:
            del self._indices[name]
            del self._indexers[name]

    def unregister_all(self):
        self._indices = {}
        self._indexers = defaultdict(list)
        self._model_indices = defaultdict(list)


registry = IndicesRegistry()


class IndexOptions(object):
    def __init__(self, meta, declared_fields):
        self.meta = getattr(meta, 'index_meta', None)
        self.optimize_query = getattr(meta, 'optimize_query', False)
        self.index = getattr(meta, 'name', None)
        self.read_consistency = getattr(meta, 'read_consistency', 'quorum')
        self.write_consistency = getattr(meta, 'write_consistency', 'quorum')
        self._declared_fields = declared_fields

    @property
    def fields(self):
        return self._declared_fields

    def get_field_by_name(self, name):
        return self._declared_fields[name]

"""
class ModelIndexOptions(object):
    def __init__(self, meta, declared_fields):
        self.optimize_query = getattr(meta, 'optimize_query', False)
        self.document = getattr(meta, 'document', None)
        self.model = getattr(meta, 'model')
        self.index = getattr(meta, 'index', None)
        self.read_consistency = getattr(meta, 'read_consistency', 'quorum')
        self.write_consistency = getattr(meta, 'write_consistency', 'quorum')
        self._declared_fields = declared_fields

    def setup_doctype(self, meta, index):
        self.document = model_doctype_factory(
                meta.model, index,
                fields=getattr(meta, 'fields', None),
                exclude=getattr(meta, 'exclude', None))
"""


class IndexerOptions(object):
    def __init__(self, meta):
        self.document = getattr(meta, 'document', None)
        self.index = getattr(meta, 'index')
        self._field_names = getattr(meta, 'fields', None) or []
        self.index_obj = registry.get(self.index)

    def get_index_instance(self):
        return self.index_obj


class ModelIndexerOptions(object):
    def __init__(self, meta):
        self.document = getattr(meta, 'document', None)
        self.index = getattr(meta, 'index')
        self.model = getattr(meta, 'model')
        self._field_names = getattr(meta, 'fields', None) or []
        self.index_obj = registry.get(self.index)

    def get_index_instance(self):
        return self.index_obj

    def setup_doctype(self, meta, index):
        self.document = model_doctype_factory(
                meta.model, index,
                fields=getattr(meta, 'fields', None),
                exclude=getattr(meta, 'exclude', None))


class IndexBase(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(IndexBase, cls).__new__

        parents = [b for b in bases if isinstance(b, IndexBase)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        meta = attrs.pop('Meta', None)
        new_class = super_new(cls, name, bases, attrs)

        if not meta:
            meta = getattr(new_class, 'Meta', None)

        declared_fields = {}
        for _attrname, _attr in new_class.__dict__.items():
            if isinstance(_attr, Field):
                declared_fields[_attrname] = _attr
                delattr(new_class, _attrname)

        setattr(new_class, '_meta', IndexOptions(meta, declared_fields))

        index_name = new_class._meta.index or generate_index_name(new_class)
        new_class._meta.index = index_name

        setattr(new_class, '_schema', Schema(declared_fields))

        registry.register(index_name, new_class)
        return new_class


class IndexerBase(type):

    def __new__(cls, name, bases, attrs):
        super_new = super(IndexerBase, cls).__new__

        parents = [b for b in bases if isinstance(b, IndexerBase)]
        if not parents or cls is ModelIndexerBase:
            return super_new(cls, name, bases, attrs)

        meta = attrs.pop('Meta', None)
        new_class = super_new(cls, name, bases, attrs)

        if not meta:
            meta = getattr(new_class, 'Meta', None)

        setattr(new_class, '_meta', IndexerOptions(meta))

        if isinstance(new_class._meta.index, (Index, IndexBase)):
            # get index name to defer initialization
            new_class._meta.index = new_class._meta.index._meta.index

        index_obj = registry.get(new_class._meta.index)

        if not new_class._meta.document:
            new_class._meta.document = index_obj.as_doctype()

        setattr(new_class, '_schema', Schema(
            new_class._meta.document.get_all_fields()))

        schema_fields = new_class._schema.get_field_names()
        for fieldname in new_class._meta._field_names:
            if fieldname not in schema_fields:
                raise FieldDoesNotExist(
                        'Field `%s` is not defined' % fieldname)

        registry.register_indexer(new_class._meta.index, new_class)
        return new_class


class ModelIndexerBase(IndexerBase):
    def __new__(cls, name, bases, attrs):
        super_new = super(ModelIndexerBase, cls).__new__

        parents = [b for b in bases if isinstance(b, ModelIndexerBase)]
        if not parents or Indexer in bases:
            return super_new(cls, name, bases, attrs)

        meta = attrs.pop('Meta', None)
        new_class = super_new(cls, name, bases, attrs)

        if not meta:
            meta = getattr(new_class, 'Meta', None)

        setattr(new_class, '_meta', ModelIndexerOptions(meta))

        if isinstance(new_class._meta.index, (Index, IndexBase)):
            # get index name to defer initialization
            new_class._meta.index = new_class._meta.index._meta.index

        if not new_class._meta.document:
            new_class._meta.setup_doctype(meta, new_class)

        setattr(new_class, '_schema', Schema(
            new_class._meta.document.get_all_fields()))

        schema_fields = new_class._schema.get_field_names()
        for fieldname in new_class._meta._field_names:
            if fieldname not in schema_fields:
                raise FieldDoesNotExist(
                        'Field `%s` is not defined' % fieldname)

        registry.register_indexer(new_class._meta.index, new_class)
        return new_class


class Index(object):
    __metaclass__ = IndexBase

    def __init__(self):
        self.indexers = []

    @property
    def name(self):
        return self._meta.index

    def get_search_object(self):
        """
        Return search object instance
        """
        return IterableSearch(index=self._meta.index)

    def initialize(self, using=None, skip_existing=False):
        """
        Initialize index and related doctypes
        """

        self.create_index(using=using, skip_existing=skip_existing)

        for indexer in self.indexers:
            indexer.initialize(using=using)

    def raw(self, data):
        return self.get_search_object().raw(data)

    def query(self, *args, **kw):
        """
        Query index
        """
        return self.get_search_object().query(*args, **kw)

    def query_string(self, query):
        """
        Query index with `query_string` and EDisMax parser.
        This is shortcut for `.query('query_string', query='<terms>',
            use_dis_max=True)`
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

    def multisearch(self, queries=None):
        """
        Create MultiSearch object
        """
        return MultiSearch(self, queries=queries)

    def clear_index(self, using=None, consistency=None):
        from elasticsearch.helpers import scan, bulk
        connection = get_connection_for_index(self._meta.index, using=using)
        objs = scan(connection, _source_include=['__non_existent_field__'])
        index_name = self._meta.index

        def document_to_action(x):
            x['_op_type'] = 'delete'
            return x

        actions = itertools.imap(document_to_action, objs)
        consistency = consistency or self._meta.write_consistency
        bulk(
            connection, actions, index=index_name, consistency=consistency,
            refresh=True)

    def create_index(self, using=None, skip_existing=False):
        from .settings import INDEX_DEFAULTS

        meta = dict(INDEX_DEFAULTS)
        meta.update(self._meta.meta or {})

        _idx = DSLIndex(self._meta.index)
        _idx.settings(**meta)

        if not skip_existing or not _idx.exists():
            _idx.create()

    def drop_index(self, using=None):
        from elasticsearch.client.indices import IndicesClient
        connection = get_connection_for_index(self._meta.index, using=using)
        return IndicesClient(connection).delete(self._meta.index)

    def as_doctype(self):
        return doctype_factory(self)

    def add_indexer(self, indexer):
        self.indexers.append(indexer(self))


class Indexer(object):
    __metaclass__ = IndexerBase

    def __init__(self, index):
        self.index = index

    def create_document(self, data, meta=None):
        """
        Create document instance based on arguments
        """

        data = dict(data)
        data['meta'] = meta or {}
        document = self._meta.document(**data)
        document.full_clean()
        return document

    def initialize(self, using=None):
        self._meta.document.init(using=using)

    def save_document(self, document, using=None):
        document.save(using=using)

    def delete_document(self, document, using=None):
        document.delete(using=using)

    def iterator(self):
        raise NotImplementedError

    def reindex(self, using=None):
        for row in self.iterator():
            doc = self.create_document(row)
            self.save_document(doc, using=using)


class ModelIndexer(Indexer):
    __metaclass__ = ModelIndexerBase

    def get_query_set(self):
        """
        Return queryset for indexing
        """
        return self.model._default_manager.all()

    def update(self, obj):
        """
        Perform create/update document only if matching indexing queryset
        """

        try:
            obj = self.get_query_set().filter(pk=obj.pk)[0]
        except IndexError:
            pass
        else:
            self.save(obj)

    def update_queryset(self, queryset):
        """
        Perform create/update of queryset but narrowed with indexing queryset
        """
        qs = self.get_query_set()
        qs.query.combine(queryset.query, 'and')
        return self.save_many(qs)

    def save(self, obj, force=False):
        doc = self.to_doctype(obj)
        doc.save()

    def save_many(
            self, objects, using=None, consistency=None, chunk_size=100,
            request_timeout=30):

        from elasticsearch.helpers import bulk

        def generate_qs():
            qs = iter(objects)
            for item in qs:
                yield self.to_doctype(item)

        doctype_name = self._meta.document._doc_type.name
        index_name = self._meta.document._doc_type.index

        connection = get_connection_for_doctype(
                self._meta.document, using=using)

        def document_to_action(x):
            data = x.to_dict()
            data['_op_type'] = 'index'
            for key, val in x.meta.to_dict().items():
                data['_%s' % key] = val
            return data

        actions = itertools.imap(document_to_action, generate_qs())
        consistency = consistency or self.index._meta.write_consistency

        return bulk(
                connection, actions, index=index_name, doc_type=doctype_name,
                consistency=consistency, refresh=True, chunk_size=chunk_size,
                request_timeout=request_timeout)[0]

    def update_index(
            self, using=None, consistency=None, chunk_size=100,
            request_timeout=30):
        self.save_many(
                self.get_query_set(), using=using,
                consistency=consistency, chunk_size=chunk_size,
                request_timeout=request_timeout)

    def delete(self, obj, fail_silently=False):
        """
        Delete document that represents specified `data` instance.

        Raise DocumentDoesNotExist exception when document does not exist.
        When `fail_silently` set to true, DocumentDoesNotExist will be
        silenced.
        """

        from elasticsearch.exceptions import NotFoundError
        doc = self.to_doctype(obj)

        try:
            doc.delete()
        except NotFoundError:
            if not fail_silently:
                raise DocumentDoesNotExist(
                    'Document `%s` (id=%s) does not exists in index `%s`' % (
                        doc._doc_type.name, doc.meta.id, self.name))

    def to_doctype(self, obj):
        """
        Convert model instance to ElasticSearch document
        """
        data = model_to_dict(obj)
        for field_name in self._meta._field_names:
            prepared_field_name = 'prepare_%s' % field_name
            if hasattr(self, prepared_field_name):
                data[field_name] = getattr(self, prepared_field_name)(obj)
        meta = {'id': obj.pk}
        return self.create_document(data, meta=meta)


"""
class ModelIndexBase(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(ModelIndexBase, cls).__new__

        parents = [b for b in bases if isinstance(b, ModelIndexBase)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        new_class = super_new(cls, name, bases, attrs)

        meta = attrs.pop('Meta', None)
        if not meta:
            meta = getattr(new_class, 'Meta', None)

        declared_fields = {}
        for _attrname, _attr in new_class.__dict__.items():
            if isinstance(_attr, Field):
                declared_fields[_attrname] = _attr

        setattr(new_class, '_meta', ModelIndexOptions(meta, declared_fields))

        if not new_class._meta.document:
            new_class._meta.setup_doctype(meta, new_class)

        index_name = new_class._meta.index or generate_index_name(new_class)
        new_class._meta.index = index_name

        setattr(new_class, '_schema', Schema(
            new_class._meta.document.get_all_fields()))

        schema_fields = new_class._schema.get_field_names()
        for fieldname in new_class._meta._field_names:
            if fieldname not in schema_fields:
                raise FieldDoesNotExist(
                        'Field `%s` is not defined' % fieldname)

        registry.register(index_name, new_class)
        return new_class


class ModelIndex(Index, ModelIndexer):
    __metaclass__ = ModelIndexBase
"""
