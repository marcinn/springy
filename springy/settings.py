from django.conf import settings

DATABASES = getattr(settings, 'ELASTIC_DATABASES', {})

AUTODISCOVER_MODULE = getattr(
        settings, 'SPRINGY_AUTODISCOVER_MODULE', 'search')

AUTODISCOVER = getattr(settings, 'SPRINGY_AUTODISCOVER', True)
