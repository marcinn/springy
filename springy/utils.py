from django.db.models import FileField
from django.db.models.options import Options
from django.utils import module_loading


if hasattr(Options, 'get_fields'):
    def get_model_fields(obj):
        return obj._meta.get_fields()
else:
    def get_model_fields(obj):
        return obj._meta.fields

if hasattr(Options, 'get_field'):
    def get_model_field(obj, x):
        return obj._meta.get_field(x)
else:
    def get_model_field(obj, x):
        return obj._meta.get_field_by_name(x)


def model_to_dict(obj, fields=None):
    fields = fields or [field.name for field in get_model_fields(obj)]
    data = {}

    for field_name in fields:
        field = get_model_field(obj, field_name)
        if getattr(field, 'is_relation', None) or getattr(
                field, 'related', None):
            if field.many_to_one:
                value = getattr(obj, field_name+'_id')
            else:
                continue
        else:
            if isinstance(field, FileField):
                value = getattr(obj, field_name)
                if value is not None:
                    value = unicode(value)  # NOQA
            else:
                value = getattr(obj, field_name)
        if value is None:
            continue
        data[field_name] = value

    return data


def index_to_string(x):
    try:
        return x._meta.index
    except AttributeError:
        pass
    return unicode(x)  # NOQA


def generate_index_name(cls):
    return '%s_%s' % (cls.__module__, cls.__name__)


def autodiscover(module_name='search'):
    module_loading.autodiscover_modules(module_name)


def chunks(iterable, chunk_size):
    for x in range(0, len(iterable), chunk_size):
        yield iterable[x:x+chunk_size]


def chunked(iterable, chunk_size):
    x = 0
    while True:
        chunk = iterable[x:x+chunk_size]
        if not chunk:
            break
        x += chunk_size
        yield chunk
