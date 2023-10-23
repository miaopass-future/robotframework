import os.path

from robot.errors import DataError
from robot.utils import Importer, is_string, split_args_from_name_or_path, type_name

from .listenermethods import LibraryListenerMethods
from .loggerapi import LoggerApi
from .loggerhelper import AbstractLoggerProxy, IsLogged
from .logger import LOGGER
from .modelcombiner import ModelCombiner


class LibraryListeners(LoggerApi):
    _method_names = ('start_suite', 'end_suite', 'start_test', 'end_test',
                     'start_keyword', 'end_keyword', 'log_message', 'message',
                     'close')
    _methods = {}

    def __init__(self, log_level='INFO'):
        self._is_logged = IsLogged(log_level)
        for name in self._method_names:
            method = LibraryListenerMethods(name)
            self._methods[name] = method

    def start_suite(self, data: 'running.TestSuite', result: 'result.TestSuite'):
        self._methods['start_suite'](ModelCombiner(data, result,
                                                   tests=data.tests,
                                                   suites=data.suites,
                                                   test_count=data.test_count))

    def end_suite(self, data: 'running.TestSuite', result: 'result.TestSuite'):
        self._methods['end_suite'](ModelCombiner(data, result))

    def start_test(self, data: 'running.TestCase', result: 'result.TestCase'):
        self._methods['start_test'](ModelCombiner(data, result))

    def end_test(self, data: 'running.TestCase', result: 'result.TestCase'):
        self._methods['end_test'](ModelCombiner(data, result))

    def start_body_item(self, data, result):
        if data.type not in (data.IF_ELSE_ROOT, data.TRY_EXCEPT_ROOT):
            self._methods['start_keyword'](ModelCombiner(data, result))

    def end_body_item(self, data, result):
        if data.type not in (data.IF_ELSE_ROOT, data.TRY_EXCEPT_ROOT):
            self._methods['end_keyword'](ModelCombiner(data, result))

    def register(self, listeners, library):
        listeners = ListenerProxy.import_listeners(listeners,
                                                   self._method_names,
                                                   prefix='_',
                                                   raise_on_error=True)
        for method in self._listener_methods():
            method.register(listeners, library)

    def _listener_methods(self):
        return [method for method in self._methods.values()
                if isinstance(method, LibraryListenerMethods)]

    def unregister(self, library, close=False):
        if close and self._methods.get('close'):
            self._methods['close'](library=library)
        for method in self._listener_methods():
            method.unregister(library)

    def new_suite_scope(self):
        for method in self._listener_methods():
            method.new_suite_scope()

    def discard_suite_scope(self):
        for method in self._listener_methods():
            method.discard_suite_scope()

    def set_log_level(self, level):
        self._is_logged.set_level(level)

    def log_message(self, message: 'model.Message'):
        if self._is_logged(message.level):
            self._methods['log_message'](message)

    def message(self, message: 'model.Message'):
        self._methods['message'](message)


class ListenerProxy(AbstractLoggerProxy):
    _no_method = None

    def __init__(self, listener, method_names, prefix=None):
        listener, name = self._import_listener(listener)
        AbstractLoggerProxy.__init__(self, listener, method_names, prefix)
        self.name = name
        self.version = self._get_version(listener)
        if self.version == 3:
            self.start_keyword = self.end_keyword = None
            self.library_import = self.resource_import = self.variables_import = None

    def _import_listener(self, listener):
        if not is_string(listener):
            # Modules have `__name__`, with others better to use `type_name`.
            name = getattr(listener, '__name__', None) or type_name(listener)
            return listener, name
        name, args = split_args_from_name_or_path(listener)
        importer = Importer('listener', logger=LOGGER)
        listener = importer.import_class_or_module(os.path.normpath(name),
                                                   instantiate_with_args=args)
        return listener, name

    def _get_version(self, listener):
        try:
            version = int(listener.ROBOT_LISTENER_API_VERSION)
            if version not in (2, 3):
                raise ValueError
        except AttributeError:
            raise DataError("Listener '%s' does not have mandatory "
                            "'ROBOT_LISTENER_API_VERSION' attribute."
                            % self.name)
        except (ValueError, TypeError):
            raise DataError("Listener '%s' uses unsupported API version '%s'."
                            % (self.name, listener.ROBOT_LISTENER_API_VERSION))
        return version

    @classmethod
    def import_listeners(cls, listeners, method_names, prefix=None,
                         raise_on_error=False):
        imported = []
        for listener in listeners:
            try:
                imported.append(cls(listener, method_names, prefix))
            except DataError as err:
                name = listener if is_string(listener) else type_name(listener)
                msg = "Taking listener '%s' into use failed: %s" % (name, err)
                if raise_on_error:
                    raise DataError(msg)
                LOGGER.error(msg)
        return imported