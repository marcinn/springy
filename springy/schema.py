from elasticsearch_dsl import DocType
from elasticsearch_dsl.exceptions import ValidationException
from django.core.exceptions import ValidationError
from .fields import doctype_field_factory
from .exceptions import DocumentDoesNotExist
from collections import OrderedDict


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

        for key in self._d_.keys():
            if not key in keys:
                del self._d_[key]

    def full_clean(self):
        try:
            super(Document, self).full_clean()
        except ValidationException, ex:
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


def model_doctype_factory(model, index, fields=None, exclude=None):
    class_name = '%sDocument' % model._meta.object_name

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
            except ValidationError, ex:
                exceptions.append(ex)
                errors[name]=unicode(ex)

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




