"""Seeded data and full-size HeavyCanvas renders without native GUI dependencies."""
import asyncio
import os
import unittest
from datetime import date
from itertools import islice
from types import SimpleNamespace
from unittest.mock import patch

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
        self.assertEqual(len({r['label'] for r in rows}), 500)
        self.assertEqual([r['label'] for r in rows], sorted(r['label'] for r in rows))
        for row in rows:
            self.assertLess(date.fromisoformat(row['label']).weekday(), 5)
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

    def test_native_presets_and_browser_limit(self):
        browser = (1000, 3000, 5000, 7500, 10000, 15000, 20000, 25000, 30000)
        native = browser + (120000, 250000, 350000, 500000, 1000000)
        for backend in ('PySide6', 'wx', 'flet', 'tkinter', 'web', 'pyodide'):
            with self.subTest(backend=backend), patch('cookbook.heavycanvas.PUI_BACKEND', backend):
                expected = browser if backend in ('web', 'pyodide') else native
                self.assertEqual(HeavyCanvasExample.sample_counts(), expected)

    def test_dates_through_500000_and_indices_above_it(self):
        labels = HeavyCanvasExample.sample_labels(500000)
        first = next(islice(labels, 20, None))
        self.assertEqual(date.fromisoformat(first).isoformat(), first)
        self.assertLess(date.fromisoformat(first).weekday(), 5)
        remaining = 0
        for last in labels:
            remaining += 1
        self.assertEqual(remaining, 499999)
        self.assertEqual(last, '2026-10-13')
        for count in (500001, 1000000):
            with self.subTest(count=count):
                labels = HeavyCanvasExample.sample_labels(count)
                self.assertEqual(next(islice(labels, 20, None)), '0')
                self.assertEqual(next(labels), '1')
                self.assertEqual(next(islice(labels, count - 3, None)), f'{count - 1:,}')
                self.assertEqual(list(labels), [])


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
        for count in HeavyCanvasExample.sample_counts():
            with self.subTest(count=count):
                self.view.state.samples = str(count)
                self.runtime.flush()
                self.view.hover(SimpleNamespace(x=400, y=100))
                self.runtime.flush()
                snapshot = self.runtime.snapshot(copy=False)
                frame = snapshot['canvases'][0]
                self.assertEqual(len(self.view._data['rows']), count)
                self.assertGreater(len(frame['commands']), 9 * count)
                self.assertTrue(all(c[3].isascii() for c in frame['commands'] if c[0] == 'text'))
                stream = RenderStream()
                stream.offer(snapshot, processed_seq=0, copy=False)
                message = dict(v=1, type='render', session='heavy', seq=1,
                               body=stream.next_render(copy=False))
                codec = StreamCodec()
                self.assertEqual(codec.pack(codec.decode(codec.encode(message))), codec.pack(message))
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
                self.assertEqual(self.view.visible_bounds(), (140, 940))
                self.assertIs(self.view._data, data)
                visible = self.view._visible_data
                self.assertIs(visible['rows'][0], data['rows'][140])
                self.assertEqual(visible, HeavyCanvasExample.chart_data(data['rows'][140:940]))
                self.view.hover(SimpleNamespace(x=300, y=120))
                self.runtime.flush()
                self.assertIs(self.view._visible_data, visible)
                self.zoom(y_delta=-40)
                self.assertEqual(self.view.visible_bounds(), (0, 1000))
                self.assertIs(self.view._visible_data, data)

        for _ in range(30):
            self.zoom(v_delta=120)
        start, stop = self.view.visible_bounds()
        self.assertEqual(stop - start, 20)
        self.assertLessEqual(abs(start + 0.7 * 20 - 0.7 * 1000), 3)
        self.zoom(v_delta=120)
        self.assertEqual(self.view.visible_bounds(), (start, stop))
        for _ in range(30):
            self.zoom(v_delta=-120)
        self.assertEqual(self.view.visible_bounds(), (0, 1000))
        self.view.leave(None)
        self.runtime.flush()
        restored = self.runtime.snapshot(copy=False)['canvases'][0]
        self.assertEqual(restored['commands'], original['commands'])

    def test_zoom_ignores_horizontal_input_and_clamps_edges(self):
        self.runtime.snapshot(copy=False)
        for deltas in (dict(h_delta=120), dict(x_delta=80), dict(delta_mode='line', delta_y=0)):
            self.zoom(**deltas)
            self.assertEqual(self.view.visible_bounds(), (0, 1000))
        for x in (0, 901):
            self.view.zoom(SimpleNamespace(x=x, y=100, v_delta=120))
            self.runtime.flush()
            self.assertEqual(self.view.visible_bounds(), (0, 1000))
        for x, expected in ((62, (0, 800)), (886, (200, 1000))):
            self.view.zoom(SimpleNamespace(x=x, y=100, v_delta=120))
            self.runtime.flush()
            self.assertEqual(self.view.visible_bounds(), expected)
            self.view.reset_zoom(None)
            self.runtime.flush()

    def test_zoom_resets_on_dataset_changes(self):
        self.runtime.snapshot(copy=False)
        self.zoom(v_delta=120)
        self.view.state.samples = '3000'
        self.runtime.flush()
        self.assertEqual(self.view.visible_bounds(), (0, 3000))
        self.view.state.samples = '1000'
        self.runtime.flush()
        self.assertEqual(self.view.visible_bounds(), (0, 1000))
        self.zoom(v_delta=120)
        self.view.regenerate(None)
        self.runtime.flush()
        self.assertEqual(self.view.visible_bounds(), (0, 1000))

    def test_large_zoom_replaces_the_chart_in_the_canvas_delta(self):
        self.view.state.samples = '30000'
        self.runtime.flush()
        original = self.runtime.snapshot(copy=False)
        frame = original['canvases'][0]
        commands = list(frame['commands'])
        self.acknowledge(frame)
        self.zoom(y_delta=120)
        target = self.runtime.snapshot(copy=False)
        self.assertEqual(self.view.visible_bounds(), (4200, 28200))
        operations = diff(original, target)
        canvas_ops = [op for op in operations if op['op'] in ('patch_canvas', 'put_canvas')]
        self.assertEqual(len(canvas_ops), 1)
        self.assertGreater(len(canvas_ops[0]['frame']['commands']), 216000)
        self.assertLess(len(target['canvases'][0]['commands']), len(commands))
        self.assertEqual(frame['commands'], commands)


if __name__ == '__main__':
    unittest.main()
