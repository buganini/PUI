"""Web application launchers forward server options without building a UI."""
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PUI.web import Application


class LaunchApp(Application):
    def setup(self):
        raise AssertionError('setup must run in a client worker')

    def content(self):
        raise AssertionError('content must run in a client worker')


class StartupTests(unittest.TestCase):
    def test_start_and_existing_run_forward_options_without_sync(self):
        options = dict(host='localhost', port=8866, base_url='/pui', mount_path='/',
                       allow_hosts=['example.com'], trusted_proxies=['192.0.2.10'],
                       session_ttl=30, max_sessions=2)
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
                app.start(factory='not_imported_yet:Application', port=8001)
                serve.assert_called_once_with('not_imported_yet:Application', port=8001)
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
                serve.assert_called_once_with('my_app:LaunchApp')
        finally:
            app.destroy(True)

    def test_run_dispatches_to_overridden_start(self):
        app = LaunchApp()
        try:
            with patch.object(app, 'start') as start:
                app.run(port=8866)
                start.assert_called_once_with(port=8866)
        finally:
            app.destroy(True)
