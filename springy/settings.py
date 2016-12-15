from django.conf import settings


DATABASES = getattr(
        settings, 'ELASTIC_DATABASES', {
            'default': {
                'hosts': 'localhost',
            }

        })

AUTODISCOVER_MODULE = getattr(
        settings, 'SPRINGY_AUTODISCOVER_MODULE', 'search')

INDEX_DEFAULTS = getattr(settings, 'ELASTIC_INDEX_DEFAULTS', {})

AUTODISCOVER = getattr(settings, 'SPRINGY_AUTODISCOVER', True)
