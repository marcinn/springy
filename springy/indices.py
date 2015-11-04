from elasticsearch_dsl import DocType, Search
from .connections import get_connection_for_doctype
from django.db.models import FileField
from .fields import doctype_field_factory
import itertools
import six


def model_doctype_factory(model, index, fields=None, exclude=None):
    class_name = '%sDocType' % model._meta.object_name

    fields = fields or [field.name for field in model._meta.get_fields()]

    if exclude:
        fields = set(fields)
        fields = list(fields.difference(fields, set(exclude)))

    parent = (object,)
    Meta = type(str('Meta'), parent, {
        'index': index,
        })

    attrs = {
            'Meta': Meta,
            }
    for field_name in fields:
        try:
            attrs[field_name]=doctype_field_factory(
                model._meta.get_field_by_name(field_name)[0])
        except TypeError:
            pass

    return type(DocType)(class_name, (DocType,), attrs)


def model_to_dict(obj, fields=None):
    fields = fields or [field.name for field in obj._meta.get_fields()]
    data = {}

    for field_name in fields:
        field = obj._meta.get_field_by_name(field_name)[0]
        if field.is_relation:
            if field.many_to_one or field.one_to_one:
                value = getattr(obj, field_name+'_id')
            else:
                continue
        else:
            if isinstance(field, FileField):
                value = getattr(obj, field_name)
                if value is not None:
                    value = unicode(value)
            else:
                value = getattr(obj, field_name)
        if value is None:
            continue
        data[field_name] = value

    return data


class IterableSearch(Search):
    """
    This class is used to make search class iterable
    (also fixes https://github.com/elastic/elasticsearch-dsl-py/issues/279)
    """

    def __iter__(self):
        return iter(self.execute())

    def __len__(self):
        return self.count()

    def execute(self):
        try:
            return self._cached_result
        except AttributeError:
            self._cached_result = super(IterableSearch, self).execute()
            return self._cached_result


class IndexOptions(object):
    def __init__(self, meta):
        self.doctype = getattr(meta, 'doctype', model_doctype_factory(
            meta.model, meta.index, fields=getattr(meta, 'fields', None),
            exclude=getattr(meta, 'exclude', None)))
        self.optimize_query = getattr(meta, 'optimize_query', False)
        self.index = getattr(meta, 'index')
        self.read_consistency = getattr(meta, 'read_consistency', 'quorum')
        self.write_consistency = getattr(meta, 'write_consistency', 'quorum')


class ModelIndexBase(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(ModelIndexBase, cls).__new__

        parents = [b for b in bases if isinstance(b, ModelIndexBase)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, attrs)

        meta = attrs.pop('Meta', None)
        if not meta:
            meta = getattr(new_class, 'Meta', None)

        setattr(new_class, '_meta', IndexOptions(meta))
        setattr(new_class, 'model', meta.model)

        return new_class


class ModelIndex(six.with_metaclass(ModelIndexBase)):
    def get_query_set(self):
        """
        Return queryset for indexing
        """
        return self.model._default_manager.all()

    def get_search_object(self):
        """
        Return search object instance
        """
        return IterableSearch(index=self._meta.doctype._doc_type.index)

    def initialize(self, using=None):
        """
        Initialize / update doctype
        """
        self._meta.doctype.init(using=using)

    def create(self, datadict, meta=None):
        """
        Create document instance based on arguments
        """
        datadict['meta'] = meta or {}
        # TODO: cleaning via DocType definition
        return self._meta.doctype(**datadict)

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
        return self.query('query_string', query=query, use_dis_max=True)

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

        doctype_name = self._meta.doctype._doc_type.name
        index_name = self._meta.doctype._doc_type.index

        connection = get_connection_for_doctype(self._meta.doctype, using=using)

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
        connection = get_connection_for_doctype(self._meta.doctype, using=using)
        objs = scan(connection, _source_include=['__non_existent_field__'])
        index_name = self._meta.doctype._doc_type.index

        def document_to_action(x):
            x['_op_type'] = 'delete'
            return x

        actions = itertools.imap(document_to_action, objs)
        consistency = consistency or self._meta.write_consistency
        bulk(connection, actions, index=index_name, consistency=consistency,
                refresh=True)

