from django.core.management.base import BaseCommand, CommandError


def confirm(question):
    value = raw_input(question+' [y/n]')  # NOQA
    if value.strip().lower() == 'y':
        return True


class Command(BaseCommand):
    help = 'Manage search indices'
    can_import_settings = True

    def add_arguments(self, parser):
        parser.add_argument(
                'command', type=str, choices=self._available_commands(),
                action='store')
        parser.add_argument(
                'index', nargs='*', type=str, metavar='INDEX',
                help='Optional index names (default: all registered)')
        parser.add_argument('--noconfirm', default=False, action='store_true')

    def _available_commands(self):
        commands = []

        for method in dir(self):
            if method.startswith('do_'):
                commands.append(method[3:])

        return commands

    def handle(self, **kw):

        command = kw.pop('command')
        indices = kw['index']
        no_confirm = kw['noconfirm']

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
            index_classes = registry.get_all()

        func(index_classes, no_confirm=no_confirm)

    def _call_indices(self, indices, method_name):
        for index_cls in indices:
            index = index_cls()
            getattr(index, method_name)()

    def do_list(self, indices, no_confirm=False):
        for index_cls in indices:
            print("%s: %s.%s" % (
                index_cls._meta.index,
                index_cls.__module__, index_cls.__name__))

        if not indices:
            print("No index regstered.")

    def do_update(self, indices, no_confirm=False):
        self._call_indices(indices, 'update_index')

    def do_clear(self, indices, no_confirm=False):
        indices_list = u'\n'.join(map(lambda x: u'\t- %s' % x, indices))
        if no_confirm or confirm(
                'This will erase all documents from indices:\n'
                '%s\n\nContinue?' % indices_list):
            self._call_indices(indices, 'clear_index')

    def do_drop(self, indices, no_confirm=False):
        indices_list = u'\n'.join(map(lambda x: u'\t- %s' % x, indices))
        if no_confirm or confirm(
                'This command will drop indices:\n'
                '%s\n\nContinue?' % indices_list):
            self._call_indices(indices, 'drop_index')

    def do_initialize(self, indices, no_confirm=False):
        self._call_indices(indices, 'initialize')
