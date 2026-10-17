"""Options handshake, worker isolation and State ref roundtrips over real IPC."""
import asyncio
import json
import multiprocessing
import unittest
from unittest.mock import patch
from aiohttp import WSMsgType
import web_server


class OptionsTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = web_server.ServerTests.asyncTearDown
    connect = web_server.ServerTests.connect
    read = web_server.ServerTests.read
    send = web_server.ServerTests.send
    nodes = web_server.ServerTests.nodes
    disconnect = web_server.ServerTests.disconnect
    wait_until = web_server.ServerTests.wait_until

    async def asyncSetUp(self):
        await web_server.ServerTests.asyncSetUp(self)
        self.gateway.factory = 'web_options_fixture:App'
        self.gateway.sessions.session_ttl = 0

    async def open_options(self, values, *, resume_id=None):
        ws = await self.connect(resume_id=resume_id, hello_changes={'capabilities': [
            'render.snapshot', 'render.patch', 'binding.object_id', 'state.refs']})
        ready = await self.read(ws)
        self.assertEqual(ready['type'], 'ready')
        self.assertIn('state.refs', ready['body']['capabilities'])
        await self.send(ws, ready['session'], 2, 'options', {'values': values})
        refs = await self.read(ws)
        self.assertEqual(refs['type'], 'state_ref')
        render = await self.read(ws)
        self.assertEqual(render['type'], 'render')
        self.assertEqual(render['body']['processed_seq'], 2)
        return ws, ready, refs, render

    async def test_options_before_import_and_setup_strings_duplicate_last_wins(self):
        values = [['example.count', '2'], ['example.count', '7'], ['text', '世界 #='],
                  ['nested', '{"a":[null,true,2.5]}'], ['plain', 'not JSON'],
                  ['nan', 'NaN'], ['deep', '[' * 65 + '0' + ']' * 65],
                  ['empty', ''], ['bool', 'true'], ['null', 'null'], ['csv', 'a,b,c'],
                  ['quoted', '"text"'], ['large_number', '9007199254740993']]
        ws, ready, refs, render = await self.open_options(values)
        expected = dict(values)
        labels = [n['props']['text'] for n in self.nodes(render) if n['type'] == 'Label']
        for prefix in ('import=', 'setup=', 'current='):
            self.assertIn(prefix + json.dumps(expected, sort_keys=True), labels)
        self.assertEqual(refs['body']['values'], [['example.count', '7']])
        self.assertEqual(render['body']['bindings'][0]['value'], 7)

    async def test_resume_keeps_state_and_new_worker_has_separate_options(self):
        ws, ready, refs, render = await self.open_options([['example.count', '7']])
        button = next(n for n in self.nodes(render) if n['type'] == 'Button')
        await self.send(ws, ready['session'], 3, 'ack',
                        {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        await self.send(ws, ready['session'], 4, 'event', {'node_id': button['id'],
            'event': 'click', 'token': button['events']['click'], 'observed_render_rev': 1, 'data': {}})
        self.assertEqual((await self.read(ws))['type'], 'result')
        self.assertEqual((await self.read(ws))['body']['values'], [['example.count', '8']])
        self.assertEqual((await self.read(ws))['type'], 'render')
        resume_id = ready['body']['resume_id']
        await self.disconnect(ws)
        await self.wait_until(lambda: self.gateway.workers[resume_id].websocket is None)
        ws, ready, refs, render = await self.open_options([['example.count', '99']], resume_id=resume_id)
        self.assertTrue(ready['body']['resumed'])
        self.assertEqual(refs['body']['values'], [['example.count', '8']])
        self.assertEqual(render['body']['bindings'][0]['value'], 8)
        _, other, refs, render = await self.open_options([['example.count', '3']])
        self.assertNotEqual(other['body']['resume_id'], resume_id)
        self.assertEqual(refs['body']['values'], [['example.count', '3']])
        self.assertIn('import={"example.count": "3"}', str(render))

    async def test_existing_binding_write_path_updates_subscription(self):
        ws, ready, refs, render = await self.open_options([])
        await self.send(ws, ready['session'], 3, 'ack',
                        {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        editor = next(n for n in self.nodes(render) if n['type'] == 'TextField')
        attachment = editor['bindings']['model']
        await self.send(ws, ready['session'], 4, 'binding_write', {
            'node_id': editor['id'], 'role': 'model', 'phase': 'commit',
            'ref': attachment['ref'], 'slot_token': attachment['slot_token'],
            'attachment_token': attachment['token'], 'observed_render_rev': 1,
            'observed_value_rev': 1, 'edit_seq': 1, 'value': '12'})
        self.assertEqual((await self.read(ws))['body']['status'], 'processed')
        self.assertEqual((await self.read(ws))['body']['values'], [['example.count', '12']])

    async def test_messages_before_options_and_repeated_options_are_rejected(self):
        ws = await self.connect(hello_changes={'capabilities': [
            'render.snapshot', 'render.patch', 'binding.object_id', 'state.refs']})
        ready = await self.read(ws)
        await self.send(ws, ready['session'], 2, 'ack',
                        {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        self.assertEqual((await self.read(ws))['type'], 'error')
        ws, ready, _, _ = await self.open_options([])
        await self.send(ws, ready['session'], 3, 'options', {'values': [['example.count', '99']]})
        self.assertEqual((await self.read(ws))['type'], 'error')

    async def test_startup_watchdog_remains_active_after_ready(self):
        self.gateway.factory = 'web_fixture:SlowStartup'
        with patch('PUI.web.server.WORKER_START_TIMEOUT', 3):
            ws = await self.connect(hello_changes={'capabilities': [
                'render.snapshot', 'render.patch', 'binding.object_id', 'state.refs']})
            ready = await self.read(ws)
            worker = self.gateway.workers[ready['body']['resume_id']]
            pid = worker.process.pid
            # Application setup cannot have started before the options message.
            self.assertFalse(web_server.block_markers(pid))
            await self.send(ws, ready['session'], 2, 'options', {'values': []})
            try:
                await self.wait_until(lambda: bool(web_server.block_markers(pid)))
                self.assertEqual((await asyncio.wait_for(ws.receive(), 5)).type, WSMsgType.CLOSE)
                await self.wait_until(lambda: not self.gateway.workers)
            finally:
                for marker in web_server.block_markers(pid):
                    marker.unlink()


class SpawnOptionsTests(OptionsTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.gateway.context = multiprocessing.get_context('spawn')


if __name__ == '__main__':
    unittest.main()
