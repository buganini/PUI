"""Single-port reverse tunneling through erebe/wstunnel."""
import asyncio
import os
import re
import shutil
import socket
import unittest
import tempfile
from unittest.mock import patch

from aiohttp import ClientSession, UnixConnector, web
from PUI.web import Application
from PUI.web.server import Gateway, serve
from PUI.web.tunnel import command, environment, lifecycle, prepare

BINARY = shutil.which('wstunnel')
URL = 'ws://127.0.0.1:8765'
OPTIONS = {'url': URL, 'token': 'test-token'}


class ConfigurationTests(unittest.TestCase):
    def test_invalid_configuration(self):
        invalid = [False, {}, URL, {'url': URL}, dict(OPTIONS, extra=True)]
        invalid += [dict(OPTIONS, url=url) for url in (
            'http://relay', 'ws://relay:bad', 'ws://relay?token=other',
            'ws://user:pass@relay', 'ws://relay/#fragment', 'ws://re lay',
            'ws://relay/a/../b', 'ws://relay//path', 'ws://relay/%2f')]
        invalid += [dict(OPTIONS, token=token) for token in ('', None, 'a/b', 'a b', '..', 'a\n')]
        for options in invalid:
            with self.subTest(options=options), self.assertRaises(ValueError):
                prepare(options)

    def test_remote_bind(self):
        for bind in ('tcp://127.0.0.1:8080', 'tcp://[::1]:0',
                     'unix://myapp/UUID', 'unix:///tmp/myapp.sock'):
            with self.subTest(bind=bind):
                config = prepare(dict(OPTIONS, bind=bind))
                self.assertEqual(command(config, '127.0.0.1', 12345)[4], bind + ':127.0.0.1:12345')
        for bind in (None, '', 'udp://localhost:80', 'tcp://localhost',
                     'tcp://localhost:65536', 'tcp://localhost:80/path',
                     'tcp://localhost:80:extra', 'unix://', 'unix:///',
                     'unix://myapp/', 'unix://myapp:extra', 'unix://bad\npath'):
            with self.subTest(bind=bind), self.assertRaisesRegex(ValueError, 'bind'):
                prepare(dict(OPTIONS, bind=bind))

    def test_lifecycle_validates_options(self):
        with self.assertRaises(ValueError):
            lifecycle({'url': URL}, '127.0.0.1', 8000)

    def test_executable_selection(self):
        self.assertEqual(prepare(OPTIONS)[0], 'wstunnel')
        for executable in ('/opt/my tools/wstunnel', 'C:/Tools/wstunnel.exe', './wstunnel'):
            config = prepare(dict(OPTIONS, wstunnel=executable))
            self.assertEqual(command(config, '127.0.0.1', 8000)[0], executable)
        for executable in ('', None, 123, 'bad\0path'):
            with self.subTest(executable=executable), self.assertRaisesRegex(ValueError, 'executable'):
                prepare(dict(OPTIONS, wstunnel=executable))

    def test_environment_isolates_tokens_and_normalizes_no_color(self):
        first = prepare(dict(OPTIONS, url=URL + '/_puitunnel'))
        second = prepare(dict(OPTIONS, token='second-token'))
        with patch.dict(os.environ, {'NO_COLOR': '1', 'WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX': 'inherited'}):
            env = environment(first)
            self.assertEqual(env['NO_COLOR'], 'true')
            self.assertEqual(env['WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX'], '_puitunnel/test-token')
            self.assertEqual(environment(second)['WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX'], 'second-token')
            self.assertEqual(os.environ['WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX'], 'inherited')
        self.assertNotIn('test-token', ' '.join(command(first, '127.0.0.1', 8000)))

    def test_resolves_binary_and_builds_tcp_command(self):
        config = prepare(dict(OPTIONS, url='wss://relay.example.com/_puitunnel/',
                              wstunnel='C:/Tools/wstunnel.exe'))
        self.assertEqual(config[2], '_puitunnel/test-token')
        args = command(config, '::1', 54321)
        self.assertEqual(args, ['C:/Tools/wstunnel.exe', 'client', '--tls-verify-certificate',
                                '-R', 'tcp://127.0.0.1:0:[::1]:54321', 'wss://relay.example.com'])

    def test_unix_rejected_before_launch(self):
        with patch('PUI.web.server._run_app') as run:
            with self.assertRaisesRegex(ValueError, 'TCP bind'):
                serve('web_fixture:App', bind='/tmp/pui-tunnel.sock', wstunnel=OPTIONS)
            run.assert_not_called()

    def test_application_forwards_options(self):
        app = Application()
        try:
            with patch('PUI.web.server.serve') as run:
                app.start(passthru=True, wstunnel=OPTIONS, bind='127.0.0.1:0')
                self.assertEqual(run.call_args.kwargs['wstunnel'], OPTIONS)
        finally:
            app.destroy(True)


class ListenerTests(unittest.IsolatedAsyncioTestCase):
    async def test_serve_binds_once_and_closes_on_startup_failure(self):
        for bind in ('127.0.0.1:0', '0.0.0.0:0'):
            captured = []
            def run(app, **kwargs):
                listener = kwargs['sock']
                captured.append(listener)
                self.assertGreater(listener.getsockname()[1], 0)
                self.assertNotIn('port', kwargs)
                raise RuntimeError('startup failure')
            with self.subTest(bind=bind), patch('PUI.web.server._run_app', side_effect=run), \
                 patch('PUI.web.tunnel.lifecycle') as context, patch('builtins.print'):
                with self.assertRaisesRegex(RuntimeError, 'startup failure'):
                    serve('web_fixture:App', bind=bind, wstunnel=OPTIONS)
                self.assertEqual(context.call_args.args[1], '127.0.0.1')
                self.assertGreater(context.call_args.args[2], 0)
                self.assertEqual(captured[0].fileno(), -1)


@unittest.skipUnless(BINARY, 'install erebe/wstunnel on PATH')
class TunnelTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_websocket_remote_port_zero_and_process_cleanup(self):
        await self.check_tunnel()

    async def test_http_websocket_remote_unix_socket(self):
        with tempfile.TemporaryDirectory(prefix='pui-', dir='/tmp') as directory:
            await self.check_tunnel(directory + '/app.sock')

    async def check_tunnel(self, socket_path=None):
        with socket.create_server(('127.0.0.1', 0)) as reservation:
            relay_port = reservation.getsockname()[1]
        token = 'pui-integration-test'
        relay = await asyncio.create_subprocess_exec(
            BINARY, '--no-color', '--log-lvl', 'info', 'server', '--restrict-http-upgrade-path-prefix', token,
            f'ws://127.0.0.1:{relay_port}', stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT, env=environment())
        children = []
        spawn = asyncio.create_subprocess_exec
        async def capture(*args, **kwargs):
            child = await spawn(*args, **kwargs)
            children.append(child)
            return child

        async def find_log(pattern):
            output = []
            while True:
                line = await relay.stdout.readline()
                if not line:
                    self.fail('wstunnel relay exited: ' + ''.join(output))
                output.append(line.decode())
                match = re.search(pattern, line.decode())
                if match:
                    return match

        proxy_tasks = set()
        requests = []
        async def proxy_connection(reader, writer):
            task = asyncio.current_task()
            proxy_tasks.add(task)
            upstream = None
            pumps = []
            try:
                header = await reader.readuntil(b'\r\n\r\n')
                requests.append(header.split(b'\r\n', 1)[0])
                # Match nginx location /_puitunnel/ + proxy_pass .../ semantics.
                if not header.startswith(b'GET /_puitunnel/'):
                    return
                remote_reader, upstream = await asyncio.open_connection('127.0.0.1', relay_port)
                upstream.write(header.replace(b'GET /_puitunnel/', b'GET /', 1))
                await upstream.drain()
                async def pump(source, target):
                    while data := await source.read(65536):
                        target.write(data)
                        await target.drain()
                pumps = [asyncio.create_task(pump(reader, upstream)),
                         asyncio.create_task(pump(remote_reader, writer))]
                await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for pump_task in pumps:
                    pump_task.cancel()
                await asyncio.gather(*pumps, return_exceptions=True)
                for stream in (writer, upstream):
                    if stream is not None:
                        stream.close()
                        await stream.wait_closed()
                proxy_tasks.discard(task)

        proxy = await asyncio.start_server(proxy_connection, '127.0.0.1', 0)
        proxy_port = proxy.sockets[0].getsockname()[1]
        runner = None
        try:
            await asyncio.wait_for(find_log(r'Starting wstunnel server listening'), 10)
            app = Gateway('web_fixture:App').application()
            async def echo(request):
                ws = web.WebSocketResponse()
                await ws.prepare(request)
                async for message in ws:
                    await ws.send_str(message.data)
                return ws
            app.router.add_get('/tunnel-echo', echo)
            with socket.create_server(('127.0.0.1', 0)) as listener:
                options = {'url': f'ws://127.0.0.1:{proxy_port}/_puitunnel', 'token': token}
                if socket_path:
                    options['bind'] = 'unix://' + socket_path
                app.cleanup_ctx.append(lifecycle(options, '127.0.0.1', listener.getsockname()[1]))
                runner = web.AppRunner(app)
                with patch.dict(os.environ, {'WSTUNNEL_HTTP_UPGRADE_PATH_PREFIX': 'wrong-inherited-token'}), \
                     patch('PUI.web.tunnel.asyncio.create_subprocess_exec', side_effect=capture):
                    await runner.setup()
                await web.SockSite(runner, listener).start()
                connector = None
                if socket_path:
                    async def wait_socket():
                        while not os.path.exists(socket_path):
                            await asyncio.sleep(0.05)
                    await asyncio.wait_for(wait_socket(), 15)
                    connector = UnixConnector(path=socket_path)
                    remote_port = 80
                else:
                    match = await asyncio.wait_for(
                        find_log(r'Starting TCP server listening cnx on 127\.0\.0\.1:(\d+)'), 15)
                    remote_port = int(match.group(1))
                    self.assertGreater(remote_port, 0)
                async with ClientSession(connector=connector) as session:
                    async with session.get(f'http://127.0.0.1:{remote_port}/') as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn('pui-root', await response.text())
                    async with session.ws_connect(f'http://127.0.0.1:{remote_port}/tunnel-echo') as ws:
                        await ws.send_str('hello')
                        self.assertEqual(await asyncio.wait_for(ws.receive_str(), 5), 'hello')
                await runner.cleanup()
                runner = None
                self.assertIsNotNone(children[0].returncode)
                self.assertTrue(requests)
                self.assertTrue(all(line == f'GET /_puitunnel/{token}/events HTTP/1.1'.encode()
                                    for line in requests))
        finally:
            if runner is not None:
                await runner.cleanup()
            proxy.close()
            await proxy.wait_closed()
            tasks = list(proxy_tasks)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if relay.returncode is None:
                relay.terminate()
            await asyncio.wait_for(relay.wait(), 5)


if __name__ == '__main__':
    unittest.main()
