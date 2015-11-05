from django.db import models
from elasticsearch_dsl import (String, Date, Integer, Boolean, Float,
        Short, Byte, Long, Double, Field, Object, Nested)


MODEL_FIELDS_MAP = {
    'DateField': Date,
    'DateTimeField': Date,
    'BooleanField': Boolean,
    'NullBooleanField': Boolean,
    'DecimalField': Float,
    'FloatField': Float,
    'PositiveSmallIntegerField': Short,
    'IntegerField': Integer,
    'PositiveIntegerField': Integer,
    'AutoField': Integer,
    'BigIntegerField': Long,
    'ForeignKey': Long,
    }


def doctype_field_factory(field, **attr):
    if field.is_relation:
        if field.many_to_many:
            raise TypeError('Field `%s` is m2m relation, which is not supported' % field.name)

    key = field.get_internal_type()

    try:
        fld = MODEL_FIELDS_MAP[key]
    except KeyError:
        fld = String

    if isinstance(fld, String) and not 'analyzer' in attrs:
        attrs['analyzer'] = 'snowball'

    return fld(**attr)

