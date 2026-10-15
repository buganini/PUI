"""Web application launchers forward server options without building a UI."""
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PUI.web import Application
from PUI.web.server import Gateway


class LaunchApp(Application):
    def setup(self):
        raise AssertionError('setup must run in a client worker')

    def content(self):
        raise AssertionError('content must run in a client worker')


class ProcessPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_context_selection_preserves_global_start_method(self):
        import multiprocessing
        before = multiprocessing.get_start_method(allow_none=True)
        for platform, method in [('linux', 'forkserver'), ('darwin', 'spawn'), ('win32', 'spawn')]:
            with self.subTest(platform=platform), \
                 patch('PUI.web.server.sys', SimpleNamespace(platform=platform)), \
                 patch('PUI.web.server.multiprocessing.set_forkserver_preload') as preload, \
                 patch('PUI.web.server.multiprocessing.get_context') as context:
                gateway = Gateway('web_fixture:App')
                context.assert_called_once_with(method)
                self.assertIs(gateway.context, context.return_value)
                if method == 'forkserver':
                    preload.assert_called_once_with([])
                else:
                    preload.assert_not_called()
        self.assertEqual(multiprocessing.get_start_method(allow_none=True), before)


class StartupTests(unittest.TestCase):
    def test_start_and_existing_run_forward_options_without_sync(self):
        options = dict(bind='localhost:8866', base_url='/pui', mount_path='/',
                       allow_hosts=['example.com'], trusted_proxies=['192.0.2.10'],
                       session_ttl=30, max_sessions=2,
                       auth=lambda username, password: username == password)
        for method in ('start', 'run'):
            with self.subTest(method=method):
                app = LaunchApp()
                try:
                    with patch('PUI.web.server.serve') as serve:
                        getattr(app, method)(**options)
                        serve.assert_called_once_with(__name__ + ':LaunchApp', **options)
                    self.assertIsNone(app.ui)
                    self.assertEqual(app.children, [])
                finally:
                    app.destroy(True)

    def test_explicit_factory_defers_application_import(self):
        app = Application()
        try:
            with patch('PUI.web.server.serve') as serve:
                app.start(factory='not_imported_yet:Application', bind='127.0.0.1:8001')
                serve.assert_called_once_with('not_imported_yet:Application', auth=None, bind='127.0.0.1:8001')
            self.assertNotIn('not_imported_yet', sys.modules)
        finally:
            app.destroy(True)

    def test_python_module_entry_resolves_importable_class(self):
        app = LaunchApp()
        try:
            with patch.object(LaunchApp, '__module__', '__main__'), \
                 patch.object(sys.modules['__main__'], '__spec__', SimpleNamespace(name='my_app')), \
                 patch('PUI.web.server.serve') as serve:
                app.start()
                serve.assert_called_once_with('my_app:LaunchApp', auth=None)
        finally:
            app.destroy(True)

    def test_run_dispatches_to_overridden_start(self):
        app = LaunchApp()
        try:
            with patch.object(app, 'start') as start:
                app.run(bind='localhost:8866')
                start.assert_called_once_with(bind='localhost:8866')
        finally:
            app.destroy(True)
