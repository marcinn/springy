from django.conf import settings

DATABASES = getattr(
        settings, 'ELASTIC_DATABASES', {
            'default': {
                'hosts': 'localhost',
            }

        })
AUTODISCOVER_MODULE = getattr(
        settings, 'SPRINGY_AUTODISCOVER_MODULE', 'search')
