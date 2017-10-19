from collections import OrderedDict

from django.core.exceptions import ValidationError
from elasticsearch_dsl import DocType
from elasticsearch_dsl.exceptions import ValidationException

from .fields import doctype_field_factory
from .exceptions import DocumentDoesNotExist, FieldDoesNotExist  # NOQA
from .utils import get_model_field


try:
    from django.db.models import (
            FieldDoesNotExist as DjangoFieldDoesNotExist)
except ImportError:
    try:
        from django.core.exceptions import (
                FieldDoesNotExist as DjangoFieldDoesNotExist)
    except ImportError:
        DjangoFieldDoesNotExist = TypeError


class Document(DocType):
    """
    Document class will represent a single Document with DocType as his meta.

    This class will be responsible for:

        * data cleaning and validation
        * data transfer between layers
        * declarative definition (subset of IndexSchema)

    Final API should look like:

    ```
    class ProductList(Document):
        class Meta:
            index = ProductIndex
            fields = ('id', 'name', 'price', 'default_picture')
    ```

    Warning!
    The Document class inherits from DocType but it will be dropped soon.
    """

    def clean_invalid_keys(self):
        """
        Remove keys not defined in doctype
        to prevent dynamic/magical/unwanted index schema mutation.
        """

        keys = self._doc_type.mapping.properties.properties._d_.keys()

        to_delete = []

        for key in self._d_.keys():
            if key not in keys:
                to_delete.append(key)

        for key in to_delete:
            del self._d_[key]

    def full_clean(self):
        try:
            super(Document, self).full_clean()
        except ValidationException as ex:
            raise ValidationError(ex)
        else:
            self.clean_invalid_keys()

        if not self._d_:
            raise ValidationError('Document can not be empty')

    def clean(self):
        pass

    def clean_fields(self):
        super(Document, self).clean_fields()

    def as_dict(self):
        return dict(self._d_)

    @classmethod
    def get_all_fields(cls):
        return cls._doc_type.mapping.properties._params['properties']


def model_doctype_factory(model, index, fields=None, exclude=None):
    class_name = '%sDocument' % model._meta.object_name

    fields = fields or [field.name for field in model._meta.get_fields()]

    if exclude:
        fields = set(fields)
        fields = list(fields.difference(fields, set(exclude)))

    parent = (object,)
    meta = {
        'index': index._meta.index,
        }

    if index._meta.doc_type:
        # elasticsearch-dsl is written in a strange way.
        # You can set empty/None as doc_type and it
        # will get this value "as is".
        #
        # This is not "pythonic". Elasticsearch-dsl have
        # more strange solutions implemented and it is
        # not reliable. Avoid elasticsearch-dsl where possible.
        #
        # Springy will drop Elasticsearch-DSL dependency soon.

        meta['doc_type'] = index._meta.doc_type

    Meta = type(str('Meta'), parent, meta)

    attrs = {
            'Meta': Meta,
            }

    for field_name in fields:
        try:
            attrs[field_name] = index._meta._declared_fields[field_name]
        except KeyError:
            try:
                field = get_model_field(model, field_name)
            except DjangoFieldDoesNotExist:
                prepare_method = 'prepare_%s' % field_name
                if hasattr(index, prepare_method):
                    raise FieldDoesNotExist(
                        'You have defined `%s()` method, '
                        'but you have missed a field declaration.\n'
                        'Add `%s` classfield to %s..' % (
                            prepare_method, field_name, type(index)))
                else:
                    raise FieldDoesNotExist(
                            'Field %s is not defined' % field_name)
            else:
                attrs[field_name] = doctype_field_factory(field)

    return type(Document)(class_name, (Document,), attrs)


class Schema(object):
    def __init__(self, fields):
        self.fields = OrderedDict(fields)

    def get_field_names(self):
        return self.fields.keys()

    def get_field_by_name(self, name):
        return self.fields[name]


class DocumentForm(object):
    def __init__(self, data=None):
        self.data = data
        self._errors = None

    def _full_clean(self, data):
        """
        Clean input data (dict-like object) by removing
        unused keys and validate input data.
        """

        errors = {}
        exceptions = []

        keys = self.fields.keys()
        cleaned_data = map(filter(lambda x: x[0] in keys, data))

        if not cleaned_data and not self.allow_empty:
            raise ValidationError('Data is empty')

        for name, field in self.fields.items():
            try:
                cleaned_data[name] = field.clean(cleaned_data.get(name))
            except ValidationError as ex:
                exceptions.append(ex)
                errors[name] = unicode(ex)  # NOQA

        self.cleaned_data = cleaned_data
        self._errors = errors
        self._is_valid = not errors

        if exceptions:
            raise exceptions[0]

    def clean(self):
        return self.cleaned_data

    @property
    def errors(self):
        if self._errors is None:
            self.is_valid()
        return self._errors

    def is_valid(self):
        try:
            self._full_clean()
        except ValidationError:
            pass
        return self._is_valid
