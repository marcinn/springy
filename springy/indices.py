from collections import defaultdict
import itertools

from .connections import get_connection_for_doctype
from .fields import Field
from .utils import model_to_dict, generate_index_name
from .search import IterableSearch, MultiSearch
from .schema import model_doctype_factory, Schema
from .exceptions import DocumentDoesNotExist, FieldDoesNotExist


class AlreadyRegisteredError(Exception):
    pass


class NotRegisteredError(KeyError):
    pass


class IndicesRegistry(object):
    def __init__(self):
        self._indices = {}
        self._model_indices = defaultdict(list)

    def register(self, name, cls):
        if not name:
            raise ValueError('Index name can not be empty')

        if name in self._indices:
            raise AlreadyRegisteredError(
                    'Index `%s` is already registered' % name)

        self._indices[name] = cls

        try:
            self._model_indices[cls.model].append(cls)
        except:
            del self._indices[name]
            raise

    def get(self, name):
        try:
            return self._indices[name]
        except KeyError:
            raise NotRegisteredError('Index `%s` is not registered' % name)

    def get_all(self):
        return self._indices.values()

    def get_for_model(self, model):
        return self._model_indices[model][:]  # shallow copy

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

    def unregister_all(self):
        self._indices = {}
        self._model_indices = defaultdict(list)


registry = IndicesRegistry()


class IndexOptions(object):
    def __init__(self, meta, declared_fields):
        self.document = getattr(meta, 'document', None)  # DocType instance
        self.doc_type = getattr(meta, 'doc_type', None)  # doc_type name
        self.optimize_query = getattr(meta, 'optimize_query', False)
        self.index = getattr(meta, 'index', None)
        self.read_consistency = getattr(meta, 'read_consistency', 'quorum')
        self.write_consistency = getattr(meta, 'write_consistency', 'quorum')
        self._field_names = getattr(meta, 'fields', None) or []
        self._declared_fields = declared_fields

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

        new_class = super_new(cls, name, bases, attrs)

        meta = attrs.pop('Meta', None)
        if not meta:
            meta = getattr(new_class, 'Meta', None)

        declared_fields = {}
        for _attrname, _attr in new_class.__dict__.items():
            if isinstance(_attr, Field):
                declared_fields[_attrname] = _attr

        setattr(new_class, '_meta', IndexOptions(meta, declared_fields))
        setattr(new_class, 'model', getattr(meta, 'model', None))

        if not new_class._meta.document:
            new_class._meta.setup_doctype(meta, new_class)

        setattr(new_class, '_schema', Schema(
            new_class._meta.document.get_all_fields()))

        schema_fields = new_class._schema.get_field_names()
        for fieldname in new_class._meta._field_names:
            if fieldname not in schema_fields:
                raise FieldDoesNotExist(
                        'Field `%s` is not defined' % fieldname)

        index_name = new_class._meta.index or generate_index_name(new_class)
        registry.register(index_name, new_class)

        return new_class


class Index(object):
    __metaclass__ = IndexBase

    @property
    def name(self):
        return self._meta.index

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
        return self.create(data, meta=meta)

    def delete(self, obj, fail_silently=False):
        """
        Delete document that represents specified `obj` instance.

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

    def save(self, obj, force=False):
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

        connection = get_connection_for_doctype(
                self._meta.document, using=using)

        def document_to_action(x):
            data = x.to_dict()
            data['_op_type'] = 'index'
            for key, val in x.meta.to_dict().items():
                data['_%s' % key] = val
            return data

        actions = itertools.imap(document_to_action, generate_qs())
        consistency = consistency or self._meta.write_consistency

        return bulk(
                connection, actions, index=index_name, doc_type=doctype_name,
                consistency=consistency, refresh=True)[0]

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

    def update_index(self, using=None, consistency=None):
        self.save_many(
                self.get_query_set(), using=using,
                consistency=consistency)

    def clear_index(self, using=None, consistency=None):
        from elasticsearch.helpers import scan, bulk
        connection = get_connection_for_doctype(
                self._meta.document, using=using)
        objs = scan(connection, _source_include=['__non_existent_field__'])
        index_name = self._meta.document._doc_type.index

        def document_to_action(x):
            x['_op_type'] = 'delete'
            return x

        actions = itertools.imap(document_to_action, objs)
        consistency = consistency or self._meta.write_consistency
        bulk(
                connection, actions, index=index_name, consistency=consistency,
                refresh=True)

    def drop_index(self, using=None):
        from elasticsearch.client.indices import IndicesClient
        connection = get_connection_for_doctype(
                self._meta.document, using=using)
        return IndicesClient(connection).delete(self._meta.index)
