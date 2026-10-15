"""A full-size Table and Canvas share the bounded render/codec budget."""
import asyncio
import unittest

from PUI.web import Application, Window, Table, Canvas, BaseTableAdapter
from PUI.web.protocol import Codec, Limits, ProtocolError, validate_data
from PUI.web.render import RenderStream
from PUI.web.runtime import Runtime


class Adapter(BaseTableAdapter):
    prefix = 'value'
    def rowCount(self): return 1000
    def columnCount(self): return 10
    def data(self, row, column): return '%s %s:%s' % (self.prefix, row, column)


class App(Application):
    def setup(self):
        self.adapter = Adapter()

    def content(self):
        with Window():
            Table(self.adapter)
            self.canvas = Canvas(self.paint)

    def paint(self, canvas):
        for i in range(10000):
            canvas.drawLine(i % 100, 0, i % 100, 100, color=0)


class CapacityTests(unittest.IsolatedAsyncioTestCase):
    async def test_large_snapshot_patch_and_recovery_roundtrip(self):
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = App()
            runtime.app.sync()
            runtime.snapshot()
            runtime.canvas_control('measure', dict(node_id=runtime.app.canvas.ui.id,
                measure_rev=1, width=100, height=100, dpr=1, visible=True))
            state = runtime.snapshot()
            with self.assertRaisesRegex(ProtocolError, 'Value count exceeds limit'):
                validate_data(state, limits=Limits(max_items=100000))
            self.assertEqual(len(state['canvases'][0]['commands']), 10000)
            stream, codec = RenderStream(), Codec()

            def transfer():
                body = stream.next_render()
                message = dict(v=1, type='render', session='capacity', seq=body['rev'], body=body)
                self.assertEqual(codec.decode(codec.encode(message)), message)
                self.assertTrue(stream.acknowledge(render_rev=body['rev'], applied_rev=body['rev'], status='applied'))
                return body

            stream.offer(state, processed_seq=1)
            self.assertEqual(transfer()['mode'], 'snapshot')
            runtime.app.adapter.prefix = 'changed'
            runtime.app.sync()
            stream.offer(runtime.snapshot(), processed_seq=2)
            patch = transfer()
            self.assertEqual(patch['mode'], 'patch')
            self.assertTrue(patch['ops'])
            stream.resync(last_applied_rev=patch['rev'])
            self.assertEqual(transfer()['mode'], 'snapshot')
        finally:
            runtime.close()
