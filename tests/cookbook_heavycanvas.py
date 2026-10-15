"""Seeded data and full-size HeavyCanvas renders without native GUI dependencies."""
import asyncio
import os
import unittest
from datetime import date
from types import SimpleNamespace

os.environ['PUI_BACKEND'] = 'web'
from cookbook.heavycanvas import HeavyCanvasExample
from PUI.web import Application, Window
from PUI.web.protocol import StreamCodec
from PUI.web.render import RenderStream
from PUI.web.runtime import Runtime


class App(Application):
    def content(self):
        with Window():
            self.example = HeavyCanvasExample()


class DataTests(unittest.TestCase):
    def test_seeded_market_data_and_indicators(self):
        data = HeavyCanvasExample.generate(500, 42)
        self.assertEqual(data, HeavyCanvasExample.generate(500, 42))
        self.assertNotEqual(data, HeavyCanvasExample.generate(500, 43))
        rows = data['rows']
        self.assertEqual(len(rows), 500)
        self.assertEqual(len({r['date'] for r in rows}), 500)
        self.assertEqual([r['date'] for r in rows], sorted(r['date'] for r in rows))
        for row in rows:
            self.assertLess(date.fromisoformat(row['date']).weekday(), 5)
            self.assertLess(row['low'], min(row['open'], row['close']))
            self.assertGreater(row['high'], max(row['open'], row['close']))
            self.assertGreater(row['volume'], 0)
            self.assertLess(row['lower'], row['mid'])
            self.assertGreater(row['upper'], row['mid'])
            for key in ('k', 'd', 'rsi'):
                self.assertTrue(0 <= row[key] <= 100)
        # First displayed bands include the hidden warmup sessions; later ones
        # must agree with the last 20 displayed closes.
        closing = [r['close'] for r in rows[-20:]]
        self.assertAlmostEqual(rows[-1]['mid'], sum(closing) / 20)


class RenderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = App()
        self.runtime.app.sync()
        self.runtime.snapshot()
        self.view = self.runtime.app.example
        self.runtime.canvas_control('measure', dict(node_id=self.view.canvas.ui.id,
            measure_rev=1, width=900, height=720, dpr=1, visible=True))

    async def asyncTearDown(self):
        self.runtime.close()

    def acknowledge(self, frame):
        self.runtime.canvas_control('canvas_ack', dict(node_id=frame['node_id'],
            frame_rev=frame['frame_rev'], measure_rev=frame['measure_rev'], status='drawn'))

    def test_every_preset_fits_render_and_transport_budgets(self):
        for count in (500, 1650, 6000):
            with self.subTest(count=count):
                self.view.state.samples = str(count)
                self.runtime.flush()
                self.view.hover(SimpleNamespace(x=400, y=100))
                self.runtime.flush()
                snapshot = self.runtime.snapshot(copy=False)
                frame = snapshot['canvases'][0]
                self.assertEqual(len(self.view._data['rows']), count)
                self.assertGreater(len(frame['commands']), 9 * count)
                self.assertTrue(all(c['text'].isascii() for c in frame['commands'] if c['op'] == 'text'))
                stream = RenderStream()
                stream.offer(snapshot, processed_seq=0, copy=False)
                message = dict(v=1, type='render', session='heavy', seq=1,
                               body=stream.next_render(copy=False))
                codec = StreamCodec()
                self.assertEqual(codec.decode(codec.encode(message)), message)
                self.acknowledge(frame)

    def test_hover_reuses_data_leave_restores_chart_and_regenerate_changes_it(self):
        original = self.runtime.snapshot(copy=False)['canvases'][0]
        self.acknowledge(original)
        data = self.view._data
        self.view.hover(SimpleNamespace(x=400, y=100))
        self.runtime.flush()
        hovered = self.runtime.snapshot(copy=False)['canvases'][0]
        self.assertIs(self.view._data, data)
        self.assertGreater(len(hovered['commands']), len(original['commands']))
        self.assertEqual(hovered['commands'][:len(original['commands'])], original['commands'])
        self.acknowledge(hovered)
        self.view.leave(None)
        self.runtime.flush()
        cleared = self.runtime.snapshot(copy=False)['canvases'][0]
        self.assertEqual(cleared['commands'], original['commands'])
        self.acknowledge(cleared)
        self.view.regenerate(None)
        self.runtime.flush()
        self.assertIsNot(self.view._data, data)
        self.assertNotEqual(self.runtime.snapshot(copy=False)['canvases'][0]['commands'], original['commands'])


if __name__ == '__main__':
    unittest.main()
