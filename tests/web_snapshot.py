"""Published records survive later model, widget and Canvas updates unchanged."""
import asyncio
from copy import deepcopy
import unittest

from PUI.web import (Application, BaseTableAdapter, Canvas, Checkbox, ComboBox,
                     ComboBoxItem, Label, Scroll, State, Table, TextField, Window)
from PUI.web.protocol import StreamCodec
from PUI.web.render import RenderStream
from PUI.web.runtime import Runtime
from web_render import apply


class Adapter(BaseTableAdapter):
    value = 'before'

    def rowCount(self): return 1
    def columnCount(self): return 1
    def data(self, row, column): return self.value


class App(Application):
    def setup(self):
        self.state = State()
        self.state.selected = ['a']
        self.state.choice = 0
        self.choice_value = {'nested': [1]}
        self.points = [[0, 0], [10, 10]]
        self.adapter = Adapter()

    def content(self):
        with Window():
            Checkbox('A', self.state('selected'), value='a')
            with ComboBox(index_model=self.state('choice')):
                ComboBoxItem('Choice', self.choice_value)
            Table(self.adapter)
            with Scroll() as self.scroll:
                Label('scroll content')
            self.canvas = Canvas(self.paint)

    def paint(self, canvas):
        canvas.drawPolyline(self.points, color=0)


class SnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_rebinding_and_list_changes_preserve_published_attachments(self):
        class Editor(Application):
            def setup(self):
                self.values = State(['before'])

            def content(self):
                with Window():
                    TextField(self.values(0))

        runtime = Runtime(asyncio.get_running_loop())
        try:
            app = runtime.app = Editor()
            app.sync()
            previous = runtime.snapshot(copy=False)
            stream = RenderStream()
            stream.offer(previous, processed_seq=0, copy=False)
            body = stream.next_render(copy=False)
            for replace_owner in (False, True):
                saved = deepcopy(previous)
                saved_body = deepcopy(body)
                if replace_owner:
                    app.values = State(['replacement'])
                else:
                    app.values.insert(0, 'inserted')
                app.redraw()
                runtime.flush()
                target = runtime.snapshot(copy=False)
                self.assertEqual(previous, saved)
                self.assertEqual(body, saved_body)
                old_editor = previous['roots'][0]['children'][0]
                new_editor = target['roots'][0]['children'][0]
                self.assertEqual(old_editor['id'], new_editor['id'])
                self.assertNotEqual(old_editor['bindings']['model']['token'],
                                    new_editor['bindings']['model']['token'])
                self.assertNotEqual(previous['bindings'][0]['token'], target['bindings'][0]['token'])
                stream.offer(target, processed_seq=body['processed_seq'] + 1, copy=False)
                stream.acknowledge(render_rev=body['rev'], applied_rev=body['rev'], status='applied')
                body = stream.next_render(copy=False)
                self.assertEqual(apply(previous, body['ops']), target)
                previous = target
        finally:
            runtime.close()

    async def test_shared_records_stay_stable_through_updates_ack_and_recovery(self):
        runtime = Runtime(asyncio.get_running_loop())
        try:
            app = runtime.app = App()
            app.sync()
            runtime.snapshot()
            runtime.canvas_control('measure', dict(node_id=app.canvas.ui.id,
                measure_rev=1, width=100, height=100, dpr=1, visible=True))
            first = runtime.snapshot(copy=False)
            self.assertIs(first['canvases'][0], app.canvas.drawing.frame)
            stream, codec, decoder = RenderStream(), StreamCodec(), StreamCodec()
            stream.offer(first, processed_seq=1, copy=False)
            initial = stream.next_render(copy=False)
            frozen = deepcopy(initial)
            self.assertIs(initial['canvases'][0], first['canvases'][0])
            message = dict(v=1, type='render', session='shared', seq=1, body=initial)
            self.assertEqual(decoder.decode(codec.encode(message)), message)

            # Application-owned inputs remain mutable; published wire records do not.
            app.state.selected.append('b')
            app.choice_value['nested'].append(2)
            app.points[0][0] = 5
            app.adapter.value = 'after'
            runtime.canvas_control('canvas_ack', {key: first['canvases'][0][key]
                for key in ('node_id', 'frame_rev', 'measure_rev')} | {'status': 'drawn'})
            app.redraw()
            runtime.flush()
            app.scroll.scrollY(42)
            target = runtime.snapshot(copy=False)
            stream.offer(target, processed_seq=2, copy=False)
            self.assertIsNone(stream.next_render(copy=False))
            self.assertIs(stream.retry(copy=False), initial)
            self.assertEqual(initial, frozen)
            self.assertEqual(first['canvases'][0]['commands'][0]['points'][0][0], 0)
            self.assertEqual(target['canvases'][0]['commands'][0]['points'][0][0], 5)
            self.assertEqual(next(s['value'] for s in first['bindings'] if s['ref']['key'] == 'selected'), ['a'])
            self.assertEqual(next(s['value'] for s in target['bindings'] if s['ref']['key'] == 'selected'), ['a', 'b'])

            # Default outputs still protect stream-owned records from callers.
            detached = stream.retry()
            detached['canvases'][0]['commands'].clear()
            self.assertEqual(stream.retry(copy=False), frozen)
            stream.acknowledge(render_rev=initial['rev'], applied_rev=initial['rev'], status='applied')
            patch = stream.next_render(copy=False)
            self.assertEqual(apply(first, patch['ops']), target)
            saved_patch = deepcopy(patch)
            message.update(seq=2, body=patch)
            self.assertEqual(decoder.decode(codec.encode(message)), message)

            # Measurement/reset/teardown replace or release producer references.
            runtime.canvas_control('measure', dict(node_id=app.canvas.ui.id,
                measure_rev=2, width=120, height=100, dpr=1, visible=True))
            runtime.snapshot(copy=False)
            runtime.reset_connection()
            runtime.close()
            self.assertEqual(initial, frozen)
            self.assertEqual(patch, saved_patch)
            stream.acknowledge(render_rev=patch['rev'], applied_rev=patch['rev'], status='applied')
            stream.resync(last_applied_rev=patch['rev'])
            recovery = stream.next_render(copy=False)
            self.assertEqual({key: recovery[key] for key in target}, target)
        finally:
            runtime.close()

    async def test_default_snapshot_detaches_canvas_frames(self):
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = App()
            runtime.app.sync()
            runtime.snapshot()
            runtime.canvas_control('measure', dict(node_id=runtime.app.canvas.ui.id,
                measure_rev=1, width=100, height=100, dpr=1, visible=True))
            frame = runtime.snapshot()['canvases'][0]
            frame['commands'][0]['points'][0][0] = 99
            self.assertEqual(runtime.snapshot()['canvases'][0]['commands'][0]['points'][0][0], 0)
        finally:
            runtime.close()


if __name__ == '__main__':
    unittest.main()
