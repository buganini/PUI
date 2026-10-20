"""Local bridge ordering, ACK credit, asyncio timers and image ownership."""
import asyncio
import math
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest

from PUI.pyodide import Application, Window, Button, Label, State, TimelineView, Canvas
from PUI.pyodide.runtime import Runtime
from PUI.pyodide.images import ImageRegistry
from PUI._browser.schema import ProtocolError


class App(Application):
    def setup(self):
        self.state = State()
        self.state.count = 0
        self.ticks = 0
        self.timer = False
        self.painter = None

    def increment(self, event):
        self.state.count += 1

    def content(self):
        self.ticks += 1
        with Window(size=(1024, 768)):
            Button('Increment').click(self.increment)
            Label(str(self.state.count))
            if self.painter is not None:
                self.canvas = Canvas(self.painter)
            if self.timer:
                TimelineView(.01)


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.messages = []
        self.runtime = Runtime(asyncio.get_running_loop(), lambda m: self.messages.append(deepcopy(m)),
                               epoch='first', build='test')
        self.app = App()
        self.app.start()
        await self.settle()

    async def test_window_initial_size_does_not_constrain_mount(self):
        window = self.app.children[0]
        self.assertIsNone(window.layout_width)
        self.assertIsNone(window.layout_height)

    async def asyncTearDown(self):
        if not self.runtime.closed:
            self.app.quit()
        await asyncio.wait_for(self.runtime.task, 1)

    async def settle(self):
        for _ in range(6):
            await asyncio.sleep(0)

    def send(self, kind, body):
        message = {'v': 1, 'epoch': 'first', 'seq': self.runtime.received + 1, 'type': kind, 'body': body}
        self.runtime.receive(message)
        return message

    def renders(self):
        return [m['body'] for m in self.messages if m['type'] == 'render']

    def ack(self):
        rev = self.renders()[-1]['rev']
        self.send('ack', {'render_rev': rev, 'applied_rev': rev, 'status': 'applied'})

    async def test_container_size_uses_the_local_bridge(self):
        window = self.app.children[0]
        binding = window.size()
        self.send('container_size', dict(node_id=window.ui.id, width=800, height=600))
        await self.settle()
        self.assertEqual(binding.value, (800, 600))
        self.assertIsNone(self.runtime.task.exception() if self.runtime.task.done() else None)

    async def test_actions_wait_for_render_credit_and_acks_do_not_generate_frames(self):
        self.assertEqual([m['type'] for m in self.messages], ['ready', 'render'])
        element = next(e for e in self.runtime.nodes.values() if e.node.wire_type == 'Button')
        body = {'node_id': element.id, 'event': 'click', 'token': element.events['click'],
                'observed_render_rev': 1, 'data': {}}
        self.send('event', body)
        self.send('event', body)
        await self.settle()
        self.assertEqual(self.app.state.count, 2)
        self.assertEqual(len(self.renders()), 1)
        self.assertEqual(len([m for m in self.messages if m['type'] == 'result']), 2)
        self.ack()
        await self.settle()
        self.assertEqual(len(self.renders()), 2)
        self.assertEqual(self.renders()[-1]['mode'], 'patch')
        self.ack()
        await self.settle()
        self.assertEqual(len(self.renders()), 2)

    async def test_duplicate_stale_malformed_and_overflow_do_not_dispatch(self):
        first = self.send('resync', {'last_applied_rev': 0})
        for bad in (first, dict(first, epoch='retired', seq=2), dict(first, seq=True),
                    dict(first, seq=2, body={'last_applied_rev': 'bad'})):
            with self.assertRaises(ProtocolError):
                self.runtime.receive(bad)
        for _ in range(255):
            self.send('resync', {'last_applied_rev': 0})
        with self.assertRaises(ProtocolError):
            self.send('resync', {'last_applied_rev': 0})
        self.runtime.incoming.clear()
        self.assertEqual(self.app.state.count, 0)

    async def test_canvas_bad_values_cross_the_local_bridge_without_closing_worker(self):
        def paint(canvas):
            canvas.drawEllipse(float('nan'), 2, -1, 3)
            canvas.drawRect(0, 0, 10, 10, fill=0xff0000)
        self.app.painter = paint
        self.app.redraw()
        self.ack()
        await self.settle()
        self.ack()
        self.send('measure', dict(node_id=self.app.canvas.ui.id, measure_rev=1,
                                  width=100, height=80, dpr=1, visible=True))
        await self.settle()
        frame = next(op['frame'] for op in self.renders()[-1]['ops'] if op['op'] == 'put_canvas')
        self.assertTrue(math.isnan(frame['commands'][0][1]))
        self.assertEqual(frame['commands'][0][3], -1)
        self.assertEqual(frame['commands'][1][5], '#ff0000')
        self.assertFalse(self.runtime.closed)
        self.ack()
        self.send('canvas_ack', {key: frame[key] for key in ('node_id', 'frame_rev', 'measure_rev')} | {'status': 'drawn'})
        await self.settle()
        self.assertFalse(self.app.canvas.drawing.awaiting)

    async def test_timer_reconciles_and_is_cancelled_on_quit(self):
        self.app.timer = True
        self.app.redraw()
        await self.settle()
        ticks = self.app.ticks
        await asyncio.sleep(.04)
        self.assertGreater(self.app.ticks, ticks)
        timer = self.app.children[0].children[-1].timer
        self.app.quit()
        await asyncio.wait_for(self.runtime.task, 1)
        self.assertTrue(timer.cancelled())
        self.assertTrue(self.runtime.closed)
        self.assertEqual(self.messages[-1]['type'], 'close')


class ImagesTests(unittest.TestCase):
    def test_revision_is_frozen_until_retired(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'example.png'
            path.write_bytes(b'first')
            registry = ImageRegistry()
            first = registry.register(path)
            self.assertEqual(registry.register(path), first)
            path.write_bytes(b'changed')
            os.utime(path, ns=(1, 2))
            second = registry.register(path)
            self.assertNotEqual(first, second)
            def state(ref):
                return {'roots': [{'type': 'Image', 'props': {'src': ref}, 'children': []}], 'canvases': []}
            entries = registry.retain([state(first), state(second)])
            self.assertEqual({e['data'] for e in entries}, {b'first', b'changed'})
            self.assertEqual([e['ref'] for e in registry.retain([state(second)])], [second])
            registry.close()
            self.assertFalse(registry.files)


class StartupWithoutAITests(unittest.IsolatedAsyncioTestCase):
    async def test_start_without_ai_package_including_unsupported_options(self):
        from unittest.mock import patch
        for options in ({}, {'codex': False, 'claude': False}, {'codex': {}}, {'claude': {}}):
            with self.subTest(options=options):
                runtime = Runtime(asyncio.get_running_loop(), lambda message: None,
                                  epoch='test', build='test')
                app = App()
                try:
                    logs = self.assertLogs('PUI', level='WARNING') if any(
                        value is not False for value in options.values()) else self.assertNoLogs('PUI')
                    with patch.dict('sys.modules', {'PUI.ai': None}), logs:
                        app.start(**options)
                    await asyncio.sleep(0)
                    self.assertIs(runtime.app, app)
                finally:
                    app.quit()
                    await asyncio.wait_for(runtime.task, 1)
