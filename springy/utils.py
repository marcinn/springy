from django.db.models import FileField
from django.utils import module_loading


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


def index_to_string(x):
    try:
        return x._meta.index
    except AttributeError:
        pass
    return unicode(x)


def generate_index_name(cls):
    return '%s_%s' % (cls.__module__, cls.__name__)


def autodiscover(module_name='search'):
    module_loading.autodiscover_modules(module_name)

