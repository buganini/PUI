"""TCP/Unix bind parsing, listener ownership and public launcher forwarding."""
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from PUI.web.server import _bind_target, _unix_listener, serve

UNIX = sys.platform != 'win32' and hasattr(socket, 'AF_UNIX')


class BindTests(unittest.TestCase):
    def test_tcp_authorities(self):
        for value, host, port in (('localhost:8866', 'localhost', 8866),
                                  ('127.0.0.1:0', '127.0.0.1', 0),
                                  ('0.0.0.0:65535', '0.0.0.0', 65535),
                                  ('[::1]:8000', '::1', 8000), ('[::]:8000', '::', 8000)):
            with self.subTest(value=value):
                self.assertEqual(_bind_target(value), dict(host=host, port=port))

    def test_invalid_bind(self):
        for value in (None, True, 8866, '', '\0socket', 'http://localhost:8866',
                      ':8000', 'localhost:', 'localhost:bad', 'localhost:-1',
                      'localhost:65536', 'localhost:80:90', '::1:8866', '[::1]',
                      'user@localhost:80', 'localhost:80?query'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _bind_target(value)

    @unittest.skipUnless(UNIX, 'Unix listener required')
    def test_socket_paths(self):
        for value in ('server.sock', './run/server.sock', '/run/pui/server.sock', './server:1.sock'):
            self.assertEqual(_bind_target(value), {'path': value})
            self.assertEqual(_bind_target(Path(value)), {'path': os.fspath(Path(value))})

    def test_windows_keeps_tcp_and_rejects_paths(self):
        with patch('PUI.web.server.sys.platform', 'win32'):
            self.assertEqual(_bind_target('localhost:8866'), dict(host='localhost', port=8866))
            with self.assertRaisesRegex(ValueError, 'use host:port'):
                _bind_target('server.sock')

    def test_cli_forwards_bind(self):
        from PUI.web.__main__ import main
        for value in ('localhost:8866', './server.sock'):
            with patch.object(sys, 'argv', ['PUI.web', 'web_fixture:App', '--bind', value]), \
                 patch('PUI.web.Application.start') as start:
                main()
                self.assertEqual(start.call_args.kwargs['bind'], value)
                self.assertNotIn('host', start.call_args.kwargs)
                self.assertNotIn('port', start.call_args.kwargs)


class ServeTests(unittest.IsolatedAsyncioTestCase):
    async def test_tcp_run_app_arguments(self):
        for bind, expected in ((None, dict(host='127.0.0.1', port=8000)),
                               ('[::1]:8866', dict(host='::1', port=8866))):
            with patch('PUI.web.server.web.run_app') as run, patch('builtins.print'):
                serve('web_fixture:App', **({} if bind is None else {'bind': bind}))
                self.assertEqual(run.call_args.kwargs, dict(expected, shutdown_timeout=3))

    @unittest.skipUnless(UNIX, 'Unix listener required')
    async def test_unix_run_app_uses_only_bound_socket_and_cleans_after_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'server.sock'
            def run(app, **kwargs):
                self.assertEqual(set(kwargs), {'sock', 'shutdown_timeout'})
                self.assertEqual(kwargs['sock'].getsockname(), str(path))
                self.assertTrue(path.is_socket())
                raise RuntimeError('startup failure')
            with patch('PUI.web.server.web.run_app', side_effect=run), patch('builtins.print'):
                with self.assertRaisesRegex(RuntimeError, 'startup failure'):
                    serve('web_fixture:App', bind=path)
            self.assertFalse(path.exists())


@unittest.skipUnless(UNIX, 'Unix listener required')
class SocketOwnershipTests(unittest.TestCase):
    def test_no_overwrite_and_cleanup_on_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'server.sock'
            with _unix_listener(path) as listener:
                listener.listen()
                before = path.stat().st_ino
                with self.assertRaises(OSError), _unix_listener(path):
                    pass
                self.assertEqual(path.stat().st_ino, before)
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.connect(str(path))
                connection, _ = listener.accept()
                connection.close()
            self.assertFalse(path.exists())
            path.write_text('keep this file')
            with self.assertRaises(OSError), _unix_listener(path):
                pass
            self.assertEqual(path.read_text(), 'keep this file')

    def test_cleanup_does_not_remove_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'server.sock'
            with _unix_listener(path):
                path.unlink()
                path.write_text('replacement')
            self.assertEqual(path.read_text(), 'replacement')


if __name__ == '__main__':
    unittest.main()
