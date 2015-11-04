from django.core.management.base import BaseCommand, CommandError


def confirm(question):
    value = raw_input(question+' [y/n]')
    if value.strip().lower()=='y':
        return True


class Command(BaseCommand):
    help = 'Manage search indices'
    can_import_settings = True

    def add_arguments(self, parser):
        parser.add_argument('command', nargs=1, type=str)
        parser.add_argument('index', nargs='*', type=str)

    def handle(self, **kw):

        command = kw['command'].pop()
        indices = kw['index']

        try:
            func = getattr(self, 'do_%s' % command)
        except AttributeError:
            raise CommandError('Unknown command `%s`' % command)

        import springy
        springy.autodiscover()

        from springy.indices import registry

        if indices:
            index_classes = map(lambda x: registry.get(x), indices)
        else:
            index_clasess = registry.get_all()

        func(index_clasess)

    def _call_indices(self, indices, method_name):
        for index_cls in indices:
            index = index_cls()
            getattr(index, method_name)()

    def do_update(self, indices):
        self._call_indices(indices, 'update_index')

    def do_clear(self, indices):
        if confirm('This will erase all documents from indexes: %s. Continue?' % indices):
            self._call_indices(indices, 'clear_index')

    def do_drop(self, indices):
        if confirm('This command will drop indexes: %s. Continue?' % indices):
            self._call_indices(indices, 'drop_index')

    def do_initialize(self, indices):
        self._call_indices(indices, 'initialize')

