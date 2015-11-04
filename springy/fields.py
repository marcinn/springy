from django.db import models
from elasticsearch_dsl import (String, Date, Integer, Boolean, Float,
        Short, Byte, Long, Double)


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
    }


def doctype_field_factory(field, **attr):
    if field.is_relation:
        raise TypeError('Relation fields are not supported')

    key = field.get_internal_type()

    try:
        fld = MODEL_FIELDS_MAP[key]
    except KeyError:
        fld = String

    if isinstance(fld, String) and not 'analyzer' in attrs:
        attrs['analyzer'] = 'snowball'

    return fld(**attr)

