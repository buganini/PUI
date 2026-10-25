"""Public start/stop owns the listener, workers and tunnel across threads."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from aiohttp import ClientSession, CookieJar, WSMsgType, web
from PUI.web import Application
from PUI.web.server import Gateway
from PUI.web.protocol import Codec, StreamCodec, SUBPROTOCOL


@contextmanager
def serving(app, **options):
    with ThreadPoolExecutor(max_workers=1) as executor:
        running = executor.submit(app.start, bind='127.0.0.1:0', **options)
        try:
            yield running
        finally:
            app.stop()
            running.result(timeout=10)


class LifecycleTests(unittest.TestCase):
    def test_ready_returns_actual_url_and_stop_closes_listener(self):
        app = Application()
        try:
            with serving(app, passthru=True, mount_path='/ui'):
                url = app.wait_started(timeout=5)
                self.assertRegex(url, r'^http://127\.0\.0\.1:[1-9]\d*/ui/$')
                with urlopen(url, timeout=5) as response:
                    self.assertIn(b'pui-root', response.read())
                app.stop()
                app.stop()
                with self.assertRaises(OSError):
                    urlopen(url, timeout=1)
        finally:
            app.destroy(True)

    def test_stop_before_thread_starts_is_remembered(self):
        app = Application()
        try:
            app.stop()
            with serving(app, passthru=True) as running:
                running.result(timeout=5)
                with self.assertRaisesRegex(RuntimeError, 'stopped before startup'):
                    app.wait_started(timeout=5)
        finally:
            app.destroy(True)

    def test_stop_during_startup_waits_for_cleanup(self):
        app = Application()
        entered = threading.Event()
        release = threading.Event()
        cleaned = threading.Event()
        original = Gateway.application
        def application(gateway):
            result = original(gateway)
            async def startup_context(_):
                entered.set()
                await asyncio.to_thread(release.wait)
                try:
                    yield
                finally:
                    await asyncio.sleep(.05)
                    cleaned.set()
            result.cleanup_ctx.append(startup_context)
            return result
        try:
            with patch.object(Gateway, 'application', application), serving(app, passthru=True), \
                    ThreadPoolExecutor(max_workers=1) as stopper:
                try:
                    self.assertTrue(entered.wait(5))
                    stopped = stopper.submit(app.stop)
                    with self.assertRaises(TimeoutError):
                        stopped.result(timeout=.05)
                finally:
                    release.set()
                stopped.result(timeout=5)
                self.assertTrue(cleaned.is_set())
                with self.assertRaisesRegex(RuntimeError, 'stopped before startup'):
                    app.wait_started(timeout=5)
        finally:
            release.set()
            app.destroy(True)

    def test_same_thread_stop_raises_instead_of_deadlocking(self):
        app = Application()
        original = Gateway.application
        def application(gateway):
            result = original(gateway)
            async def stop(request):
                try:
                    app.stop()
                except RuntimeError as error:
                    return web.Response(text=str(error))
                raise AssertionError('stop should reject its own thread')
            result.router.add_get('/stop-test', stop)
            return result
        try:
            with patch.object(Gateway, 'application', application), serving(app, passthru=True):
                url = app.wait_started(timeout=5)
                with urlopen(url + 'stop-test', timeout=5) as response:
                    self.assertIn(b'Web server thread', response.read())
        finally:
            app.destroy(True)

    def test_startup_failure_wakes_waiters_and_allows_restart(self):
        app = Application()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                running = executor.submit(app.start, passthru=True, wstunnel={'url': 'bad'})
                with self.assertRaises(ValueError):
                    app.wait_started(timeout=5)
                with self.assertRaises(ValueError):
                    running.result(timeout=5)
            app.stop()
            # Wait for a new start to enter before asking for that run's result.
            entered = threading.Event()
            original = Gateway.application
            def application(gateway):
                entered.set()
                return original(gateway)
            with patch.object(Gateway, 'application', application), serving(app, passthru=True):
                self.assertTrue(entered.wait(5))
                self.assertTrue(app.wait_started(timeout=5).startswith('http://'))
                with self.assertRaisesRegex(RuntimeError, 'already'):
                    app.start(passthru=True)
        finally:
            app.destroy(True)

    @unittest.skipUnless(shutil.which('wstunnel'), 'install erebe/wstunnel on PATH')
    def test_stop_reaps_tunnel_process(self):
        app = Application()
        children = []
        spawn = asyncio.create_subprocess_exec
        async def capture(*args, **kwargs):
            child = await spawn(*args, **kwargs, stdout=asyncio.subprocess.DEVNULL,
                                stderr=asyncio.subprocess.DEVNULL)
            children.append(child)
            return child
        try:
            with socket.create_server(('127.0.0.1', 0)) as relay:
                options = {'url': f'ws://127.0.0.1:{relay.getsockname()[1]}', 'token': 'test'}
                with patch('PUI.web.tunnel.asyncio.create_subprocess_exec', side_effect=capture), \
                        serving(app, passthru=True, wstunnel=options):
                    app.wait_started(timeout=5)
                    self.assertEqual(len(children), 1)
                    self.assertIsNone(children[0].returncode)
                    app.stop()
                    self.assertIsNotNone(children[0].returncode)
        finally:
            app.destroy(True)

    def test_failed_tunnel_launch_cleans_up_started_contexts(self):
        app = Application()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                running = executor.submit(app.start, bind='127.0.0.1:0', passthru=True,
                    wstunnel={'url': 'ws://127.0.0.1:8765', 'token': 'test',
                              'wstunnel': '/nonexistent/pui-test-wstunnel'})
                with self.assertRaises(FileNotFoundError):
                    app.wait_started(timeout=5)
                with self.assertRaises(FileNotFoundError):
                    running.result(timeout=5)
            # A failed runner.setup() must release the single-passthru guard.
            other = Application()
            try:
                with serving(other, passthru=True):
                    self.assertTrue(other.wait_started(timeout=5).startswith('http://'))
            finally:
                other.destroy(True)
        finally:
            app.destroy(True)

    @unittest.skipUnless(hasattr(socket, 'AF_UNIX'), 'Unix socket required')
    def test_unix_socket_removed_before_stop_returns(self):
        app = Application()
        try:
            with tempfile.TemporaryDirectory(prefix='pui-', dir='/tmp') as directory, \
                    ThreadPoolExecutor(max_workers=1) as executor:
                path = str(Path(directory) / 'web.sock')
                running = executor.submit(app.start, bind=path, passthru=True)
                try:
                    self.assertEqual(app.wait_started(timeout=5), path)
                    self.assertTrue(Path(path).is_socket())
                finally:
                    app.stop()
                self.assertFalse(Path(path).exists())
                running.result(timeout=5)
        finally:
            app.destroy(True)

    @unittest.skipIf(sys.platform == 'win32', 'POSIX signal test')
    def test_sigterm_cleans_main_thread_server(self):
        with tempfile.TemporaryDirectory(prefix='pui-', dir='/tmp') as directory:
            path = str(Path(directory) / 'web.sock')
            process = subprocess.Popen([sys.executable, '-m', 'PUI.web', 'web_fixture:App',
                                        '--bind', path, '--passthru'],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    line = executor.submit(process.stdout.readline).result(timeout=10)
                self.assertIn('PUI Web:', line)
                process.send_signal(signal.SIGTERM)
                output, _ = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, output)
                self.assertFalse(Path(path).exists())
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate()


class WorkerShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_stop_drains_websocket_and_live_worker(self):
        for passthru in (False, True):
            with self.subTest(passthru=passthru):
                app = Application()
                gateways = []
                original = Gateway.application
                def application(gateway):
                    gateways.append(gateway)
                    return original(gateway)
                try:
                    with patch.object(Gateway, 'application', application), \
                            serving(app, factory='web_fixture:App', passthru=passthru):
                        url = await asyncio.to_thread(app.wait_started, 5)
                        async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as client:
                            async with client.get(url) as response:
                                html = await response.text()
                            build = re.search(r'data-build="([^"]+)"', html).group(1)
                            async with client.ws_connect(url + 'pui/ws', protocols=[SUBPROTOCOL],
                                                         headers={'Origin': url.rstrip('/')}) as ws:
                                await ws.send_bytes(Codec().encode({'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
                                    'body': {'client_build': build, 'capabilities': [
                                        'render.snapshot', 'render.patch', 'binding.object_id'],
                                        'viewport': {'width': 100, 'height': 100, 'dpr': 1}, 'resume_id': None}}))
                                decoder = StreamCodec()
                                try:
                                    ready = decoder.decode((await asyncio.wait_for(ws.receive(), 10)).data)
                                finally:
                                    decoder.close()
                                worker = gateways[0].workers[ready['body']['resume_id']]
                                if not passthru:
                                    self.assertTrue(worker.process.is_alive())
                                    worker_pid = worker.process.pid
                                stopping = asyncio.create_task(asyncio.to_thread(app.stop))
                                while True:
                                    message = await asyncio.wait_for(ws.receive(), 10)
                                    if message.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR):
                                        break
                                await asyncio.wait_for(stopping, 10)
                                self.assertEqual(gateways[0].workers, {})
                                if passthru:
                                    self.assertTrue(worker.application_task.done())
                                else:
                                    import multiprocessing
                                    self.assertNotIn(worker_pid, [child.pid for child in multiprocessing.active_children()])
                                    with self.assertRaisesRegex(ValueError, 'closed'):
                                        worker.process.is_alive()
                finally:
                    app.destroy(True)


if __name__ == '__main__':
    unittest.main()
