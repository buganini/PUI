"""Canvas recording, measurements and presentation credit without a GUI toolkit."""
import asyncio
import unittest
from copy import deepcopy
from PUI.web import Application, Window, Canvas, Anchor
from PUI.web.runtime import Runtime
from PUI.web.protocol import ProtocolError


class App(Application):
    def setup(self):
        self.paints = 0
        self.continuous = False
        self.color = 0xff0000

    def content(self):
        with Window():
            self.canvas = Canvas(self.paint).style(bgColor=0xffffff)

    def paint(self, c):
        self.paints += 1
        c.drawLine(1, 2, 3, 4, color=0)
        c.drawPolyline([(0, 0), (4, 4)], color=0)
        c.drawCubicBezier((0, 0), (0, 4), (4, 0), (4, 4), color=0)
        c.drawPolygon([(0, 0), (4, 4), (0, 4)], fill=0)
        c.drawRect(10, 10, 1, 1, fill=self.color)
        c.drawEllipse(5, 5, 3, 2, stroke=0)
        c.drawText(5, 5, 'line1\nline2', w=4, h=6, anchor=Anchor.CENTER, rotate=30)
        return self.continuous


class CanvasTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = App()
        self.runtime.app.sync()
        self.runtime.snapshot()

    async def asyncTearDown(self):
        self.runtime.close()

    def measure(self, rev=1, **changes):
        data = dict(node_id=self.runtime.app.canvas.ui.id, measure_rev=rev,
                    width=120, height=80, dpr=2, visible=True)
        data.update(changes)
        return self.runtime.canvas_control('measure', data)

    def frame(self):
        return self.runtime.snapshot()['canvases'][0]

    def ack(self, frame, status='drawn'):
        return self.runtime.canvas_control('canvas_ack',
            {key: frame[key] for key in ('node_id', 'frame_rev', 'measure_rev')} | {'status': status})

    def test_no_paint_before_positive_visible_measurement(self):
        self.assertEqual(self.runtime.snapshot()['canvases'], [])
        self.measure(width=0)
        self.assertEqual(self.runtime.snapshot()['canvases'], [])
        self.measure(2, visible=False)
        self.assertEqual(self.runtime.snapshot()['canvases'], [])
        self.assertEqual(self.runtime.app.paints, 0)
        self.measure(3)
        frame = self.frame()
        self.assertEqual((self.runtime.app.canvas.width, self.runtime.app.canvas.height,
                          self.runtime.app.canvas.pixel_density), (120, 80, 2))
        self.assertEqual([c['op'] for c in frame['commands']],
                         ['line', 'polyline', 'cubic', 'polygon', 'rect', 'ellipse', 'text'])
        self.assertEqual(frame['commands'][4]['fill'], '#ff0000')
        self.assertEqual(frame['commands'][-1]['anchor'], 'CENTER')

    def test_dirty_painters_wait_for_presentation_not_dom_snapshots(self):
        self.measure()
        frame = deepcopy(self.frame())
        self.runtime.app.color = 0x00ff00
        self.runtime.app.sync()
        self.assertEqual(self.frame(), frame)
        self.assertEqual(self.runtime.app.paints, 1)
        self.assertTrue(self.ack(frame))
        second = self.frame()
        self.assertEqual(second['commands'][4]['fill'], '#00ff00')
        self.assertFalse(self.ack(frame))
        self.assertEqual(self.frame(), second)

    def test_continuous_credit_is_single_use_and_measurement_scoped(self):
        self.runtime.app.continuous = True
        self.measure()
        frame = self.frame()
        self.assertTrue(self.ack(frame))
        self.assertFalse(self.ack(frame, 'unchanged'))
        second = self.frame()
        self.assertEqual(self.runtime.app.paints, 2)
        self.assertTrue(self.measure(2, width=240))
        self.assertFalse(self.measure(1))
        self.assertFalse(self.ack(second))
        third = self.frame()
        self.assertEqual(third['measure_rev'], 2)
        self.assertEqual(third['width'], 240)
        self.assertFalse(self.ack(third, 'hidden'))
        self.assertEqual(self.frame(), third)

    def test_hiding_and_reconnection_retire_measurements_and_frames(self):
        self.measure()
        frame = self.frame()
        self.measure(2, visible=False, width=0, height=0)
        self.assertEqual(self.runtime.snapshot()['canvases'], [])
        self.assertFalse(self.ack(frame))
        self.runtime.reset_connection()
        self.assertTrue(self.measure(1))
        restored = self.frame()
        self.assertGreater(restored['frame_rev'], frame['frame_rev'])
        self.assertFalse(self.ack(frame))

    def test_bad_measurements_and_drawing_arguments_are_explicit(self):
        for bad in ({'dpr': 0}, {'width': True}, {'width': 1e6}, {'width': 4096, 'height': 4096, 'dpr': 2}):
            with self.subTest(bad=bad), self.assertRaises(ProtocolError):
                self.measure(**bad)
        self.measure()
        self.runtime.app.canvas.painter = lambda c: c.drawEllipse(0, 0, -1, 1)
        with self.assertRaises(ValueError):
            self.frame()
        with self.assertRaises(RuntimeError):
            self.runtime.app.canvas.drawLine(0, 0, 1, 1)
