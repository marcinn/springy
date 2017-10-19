from django.apps import AppConfig


class SpringyAppConfig(AppConfig):
    name = 'springy'
    verbose_name = 'Springy'

    def ready(self):
        from elasticsearch_dsl.connections import connections
        from .settings import DATABASES, AUTODISCOVER_MODULE, AUTODISCOVER
        from .utils import autodiscover

        connections.configure(**DATABASES)

        if AUTODISCOVER:
            autodiscover(AUTODISCOVER_MODULE)
