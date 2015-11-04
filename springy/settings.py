from django.conf import settings

DATABASES = getattr(settings, 'ELASTIC_DATABASES', {})

