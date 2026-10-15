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
from PUI.web.render import RenderStream, diff
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

    def zoom(self, **deltas):
        self.view.zoom(SimpleNamespace(x=62 + (900 - 76) * 0.7, y=100, **deltas))
        self.runtime.flush()

    def test_wheel_units_anchor_bounds_and_cached_indicators(self):
        original = self.runtime.snapshot(copy=False)['canvases'][0]
        self.acknowledge(original)
        data = self.view._data
        for deltas in (dict(v_delta=120), dict(y_delta=40),
                       dict(delta_mode='line', delta_y=-3), dict(delta_mode='page', delta_y=-1)):
            with self.subTest(deltas=deltas):
                self.view.reset_zoom(None)
                self.runtime.flush()
                self.zoom(**deltas)
                self.assertEqual(self.view.visible_bounds(), (70, 470))
                self.assertIs(self.view._data, data)
                visible = self.view._visible_data
                self.assertIs(visible['rows'][0], data['rows'][70])
                self.assertEqual(visible, HeavyCanvasExample.chart_data(data['rows'][70:470]))
                self.view.hover(SimpleNamespace(x=300, y=120))
                self.runtime.flush()
                self.assertIs(self.view._visible_data, visible)
                self.zoom(y_delta=-40)
                self.assertEqual(self.view.visible_bounds(), (0, 500))
                self.assertIs(self.view._visible_data, data)

        for _ in range(30):
            self.zoom(v_delta=120)
        start, stop = self.view.visible_bounds()
        self.assertEqual(stop - start, 20)
        self.assertLessEqual(abs(start + 0.7 * 20 - 0.7 * 500), 3)
        self.zoom(v_delta=120)
        self.assertEqual(self.view.visible_bounds(), (start, stop))
        for _ in range(30):
            self.zoom(v_delta=-120)
        self.assertEqual(self.view.visible_bounds(), (0, 500))
        self.view.leave(None)
        self.runtime.flush()
        restored = self.runtime.snapshot(copy=False)['canvases'][0]
        self.assertEqual(restored['commands'], original['commands'])

    def test_zoom_ignores_horizontal_input_and_clamps_edges(self):
        self.runtime.snapshot(copy=False)
        for deltas in (dict(h_delta=120), dict(x_delta=80), dict(delta_mode='line', delta_y=0)):
            self.zoom(**deltas)
            self.assertEqual(self.view.visible_bounds(), (0, 500))
        for x in (0, 901):
            self.view.zoom(SimpleNamespace(x=x, y=100, v_delta=120))
            self.runtime.flush()
            self.assertEqual(self.view.visible_bounds(), (0, 500))
        for x, expected in ((62, (0, 400)), (886, (100, 500))):
            self.view.zoom(SimpleNamespace(x=x, y=100, v_delta=120))
            self.runtime.flush()
            self.assertEqual(self.view.visible_bounds(), expected)
            self.view.reset_zoom(None)
            self.runtime.flush()

    def test_zoom_resets_on_dataset_changes(self):
        self.runtime.snapshot(copy=False)
        self.zoom(v_delta=120)
        self.view.state.samples = '1650'
        self.runtime.flush()
        self.assertEqual(self.view.visible_bounds(), (0, 1650))
        self.view.state.samples = '500'
        self.runtime.flush()
        self.assertEqual(self.view.visible_bounds(), (0, 500))
        self.zoom(v_delta=120)
        self.view.regenerate(None)
        self.runtime.flush()
        self.assertEqual(self.view.visible_bounds(), (0, 500))

    def test_large_zoom_replaces_the_chart_in_the_canvas_delta(self):
        self.view.state.samples = '6000'
        self.runtime.flush()
        original = self.runtime.snapshot(copy=False)
        frame = original['canvases'][0]
        commands = list(frame['commands'])
        self.acknowledge(frame)
        self.zoom(y_delta=120)
        target = self.runtime.snapshot(copy=False)
        self.assertEqual(self.view.visible_bounds(), (840, 5640))
        operations = diff(original, target)
        canvas_ops = [op for op in operations if op['op'] in ('patch_canvas', 'put_canvas')]
        self.assertEqual(len(canvas_ops), 1)
        self.assertGreater(len(canvas_ops[0]['frame']['commands']), 43000)
        self.assertLess(len(target['canvases'][0]['commands']), len(commands))
        self.assertEqual(frame['commands'], commands)


if __name__ == '__main__':
    unittest.main()
