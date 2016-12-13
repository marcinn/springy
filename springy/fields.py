from elasticsearch_dsl.field import (  # NOQA
        String, Date, Integer, Boolean, Float,
        Short, Byte, Long, Double, Field, Object, Nested,
        GeoShape)


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


def doctype_field_factory(field, **attrs):
    if getattr(field, 'is_relation', None) or getattr(field, 'related', None):
        if field.many_to_many:
            raise TypeError(
                    'Field `%s` is m2m relation, '
                    'which is not supported' % field.name)

    key = field.get_internal_type()

    try:
        fld = MODEL_FIELDS_MAP[key]
    except KeyError:
        fld = String

    if isinstance(fld, String) and 'analyzer' not in attrs:
        attrs['analyzer'] = 'snowball'

    return fld(**attrs)
