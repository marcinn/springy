from django.apps import AppConfig


class SpringyAppConfig(AppConfig):
    name = 'springy'
    verbose_name = 'Springy'

    def ready(self):
        from .settings import DATABASES, AUTODISCOVER_MODULE
        from .utils import autodiscover
        from elasticsearch_dsl.connections import connections

        connections.configure(**DATABASES)
        autodiscover(AUTODISCOVER_MODULE)
