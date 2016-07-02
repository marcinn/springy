from django.apps import AppConfig


class SpringyAppConfig(AppConfig):
    name = 'springy'
    verbose_name = 'Springy'

    def ready(self):
        from .settings import DATABASES
        from elasticsearch_dsl.connections import connections
        connections.configure(**DATABASES)
