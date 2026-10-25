"""In-process startup, browser handshake and runtime cleanup."""
import asyncio
import os
import sys
import threading
import unittest
from unittest.mock import patch

from aiohttp import ClientSession, CookieJar
from aiohttp.test_utils import TestServer
from PUI.web import Application, Window, Label, Button, State
from PUI.web.protocol import Codec, StreamCodec, SUBPROTOCOL
from PUI.web.server import Gateway, serve
from PUI._browser import widgets
from PUI.options import Options


class PassthruTests(unittest.IsolatedAsyncioTestCase):
    async def test_instance_runs_in_caller_and_restores_globals(self):
        calls = []
        state = State()
        state.count = 0
        class LocalApp(Application):
            def content(self):
                calls.append((os.getpid(), threading.get_ident()))
                with Window('Passthru'):
                    Label(str(state.count))
                    Button('Increment').click(self.increment)

            def increment(self, event):
                state.count += 1
        app = LocalApp()
        previous_runtime = widgets._current_runtime
        previous_options = dict(Options)
        with patch('PUI.web.server.multiprocessing.get_context', side_effect=AssertionError('process context')):
            gateway = Gateway(lambda: app, passthru=True)
        self.assertEqual(gateway.sessions.max_sessions, 1)
        self.assertEqual(gateway.sessions.session_ttl, 0)
        async with TestServer(gateway.application()) as server:
            async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as client:
                async with client.get(server.make_url('/')) as response:
                    self.assertEqual(response.status, 200)
                    html = await response.text()
                    self.assertIn('data-passthru="true"', html)
                    self.assertNotIn('data-renew=', html)
                    self.assertNotIn('data-logout=', html)
                for action in ('renew', 'logout'):
                    async with client.post(server.make_url('/pui/' + action)) as response:
                        self.assertEqual(response.status, 404)
                async with client.ws_connect(server.make_url('/pui/ws'), protocols=[SUBPROTOCOL],
                        headers={'Origin': str(server.make_url('/')).rstrip('/')}) as ws:
                    await ws.send_bytes(Codec().encode({'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
                        'body': {'client_build': gateway.build, 'capabilities': [
                            'render.snapshot', 'render.patch', 'binding.object_id'],
                            'viewport': {'width': 100, 'height': 100, 'dpr': 1}, 'resume_id': None}}))
                    decoder = StreamCodec()
                    try:
                        ready = decoder.decode((await asyncio.wait_for(ws.receive(), 5)).data)
                        frame = decoder.decode((await asyncio.wait_for(ws.receive(), 5)).data)
                        button = next(node for node in frame['body']['roots'][0]['children']
                                      if node['type'] == 'Button')
                        for seq, kind, body in (
                                (2, 'ack', {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'}),
                                (3, 'event', {'node_id': button['id'], 'event': 'click',
                                    'token': button['events']['click'], 'observed_render_rev': 1, 'data': {}})):
                            await ws.send_bytes(Codec().encode({'v': 1, 'type': kind,
                                'session': ready['session'], 'seq': seq, 'body': body}))
                        async def updated():
                            while state.count != 1:
                                await asyncio.sleep(.01)
                        await asyncio.wait_for(updated(), 5)
                    finally:
                        decoder.close()
                    self.assertEqual(frame['type'], 'render')
                    worker = gateway.workers[ready['body']['resume_id']]
                    self.assertIsNone(worker.process)
                    self.assertFalse(worker.application_task.done())
                    self.assertIs(app.runtime.app, app)
                    self.assertTrue(calls)
                    self.assertTrue(all(call == (os.getpid(), threading.get_ident()) for call in calls))
        self.assertTrue(app.destroyed)
        self.assertTrue(worker.application_task.done())
        self.assertEqual(gateway.workers, {})
        self.assertIs(widgets._current_runtime, previous_runtime)
        self.assertEqual(dict(Options), previous_options)

    async def test_background_thread_disables_signals(self):
        with patch('PUI.web.server._run_app') as run, patch('builtins.print'):
            await asyncio.to_thread(serve, 'web_fixture:App', passthru=True)
            self.assertFalse(run.call_args.kwargs['handle_signals'])

    async def test_instance_start_and_cli(self):
        with patch('PUI.web.server.serve') as server:
            app = Application()
            app.start(passthru=True)
            self.assertIs(server.call_args.args[0](), app)
            self.assertTrue(server.call_args.kwargs['passthru'])
        from PUI.web.__main__ import main
        with patch.object(sys, 'argv', ['PUI.web', 'web_fixture:App', '--passthru']), \
                patch('PUI.web.Application.start') as start:
            main()
            self.assertTrue(start.call_args.kwargs['passthru'])

    async def test_rejects_process_only_features(self):
        for option in ('landlock', 'codex', 'claude'):
            with self.subTest(option=option), self.assertRaisesRegex(ValueError, 'passthru'):
                Gateway('web_fixture:App', passthru=True, **{option: {}})


if __name__ == '__main__':
    unittest.main()
