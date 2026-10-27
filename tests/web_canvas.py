"""Canvas recording, measurements and presentation credit without a GUI toolkit."""
import asyncio
import math
import unittest
from copy import deepcopy
from PUI.web import Application, Window, Canvas, Anchor
from PUI.web.runtime import Runtime
from PUI.web.protocol import Codec, ProtocolError, StreamCodec
from PUI.web.render import RenderStream
from PUI._browser.canvas import _integer_color, command_color


class ColorTests(unittest.TestCase):
    def setUp(self):
        _integer_color.cache_clear()
        self.addCleanup(_integer_color.cache_clear)

    def test_integer_colors_keep_existing_formatting(self):
        for value, expected in ((0, '#000000'), (0x71B7FF, '#71b7ff'),
                                (0xffffff, '#ffffff'), (0xffffffff, '#ffffff00'),
                                (0x1000000, '#000000fe')):
            self.assertEqual(command_color(value), expected)
            self.assertEqual(command_color(value), expected)
        self.assertEqual(_integer_color.cache_info().hits, 5)

    def test_lru_retains_recent_colors_and_stays_within_128_entries(self):
        for color in range(128):
            command_color(color)
        self.assertEqual(_integer_color.cache_info().currsize, 128)
        command_color(0)  # Refresh the oldest entry before inserting a new one.
        command_color(128)
        before = _integer_color.cache_info()
        command_color(0)
        self.assertEqual(_integer_color.cache_info().hits, before.hits + 1)
        command_color(1)  # The least recently used entry was evicted.
        self.assertEqual(_integer_color.cache_info().misses, before.misses + 1)
        for color in range(129, 1000):
            command_color(color)
        self.assertEqual(_integer_color.cache_info().currsize, 128)

    def test_non_integer_values_bypass_cache_unchanged(self):
        class IntSubclass(int):
            pass
        for value in (None, True, False, 1.0, 'red', '#71b7ff', [], {}, IntSubclass(7)):
            self.assertIs(command_color(value), value)
        self.assertEqual(_integer_color.cache_info().currsize, 0)
        self.assertEqual(_integer_color.cache_info().misses, 0)


class App(Application):
    def setup(self):
        self.paints = 0
        self.continuous = False
        self.color = 0xff0000
        self.show = True

    def content(self):
        with Window():
            if self.show:
                self.canvas = Canvas(self.paint).style(bgColor=0xffffff)

    def paint(self, c):
        self.paints += 1
        c.drawLine(1, 2, 3, 4, color=0)
        c.drawPolyline([(0, 0), (4, 4)], color=0)
        c.drawCubicBezier((0, 0), (0, 4), (4, 0), (4, 4), color=0)
        c.drawPolygon([(0, 0), (4, 4), (0, 4)], fill=0)
        c.drawRect(10, 10, 1, 1, fill=self.color)
        c.drawEllipse(5, 5, 3, 2, stroke=0)
        c.drawText(5, 5, 'line1\nline2', w=4, h=6, anchor=Anchor.Center, rotate=30)
        return self.continuous


class CanvasTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = App()
        self.runtime.app.sync()
        self.runtime.snapshot()

    async def asyncTearDown(self):
        self.runtime.close()

    async def test_minimum_dimensions_are_published_separately(self):
        node = self.runtime.app.canvas
        node.layout(minWidth=160, minHeight=100)
        node.update(node)
        snapshot = self.runtime.snapshot()
        layout = snapshot['roots'][0]['children'][0]['layout']
        self.assertEqual((layout['minWidth'], layout['minHeight']), (160, 100))
        self.assertNotIn('width', layout)
        self.assertNotIn('height', layout)

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
        self.assertEqual([c[0] for c in frame['commands']],
                         ['line', 'polyline', 'cubic', 'polygon', 'rect', 'ellipse', 'text'])
        self.assertEqual(frame['commands'][4][5], '#ff0000')
        self.assertEqual(frame['commands'][-1][9], 'Center')

    def test_failed_image_frame_does_not_continue_animation(self):
        self.runtime.app.continuous = True
        self.measure()
        frame = self.frame()
        self.assertTrue(frame['continue'])
        self.assertFalse(self.ack(frame, 'failed'))
        self.assertFalse(self.runtime.app.canvas.drawing.awaiting)
        self.assertFalse(self.runtime.app.canvas.drawing.dirty)

    def test_command_positions_and_messagepack_arrays(self):
        self.measure()
        frame = self.frame()
        expected = [
            ('line', 1, 2, 3, 4, '#000000', 1),
            ('polyline', [[0, 0], [4, 4]], '#000000', 1),
            ('cubic', [0, 0], [0, 4], [4, 0], [4, 4], '#000000', 1),
            ('polygon', [[0, 0], [4, 4], [0, 4]], '#000000', None, 1),
            ('rect', 10, 10, 1, 1, '#ff0000', None, 1),
            ('ellipse', 5, 5, 3, 2, None, '#000000', 1),
            ('text', 5, 5, 'line1\nline2', 4, 6, 12, None, 30, 'Center'),
        ]
        self.assertEqual(frame['commands'], expected)
        message = dict(v=1, type='render', session='commands', seq=1, body={'frame': frame})
        decoded = StreamCodec().decode(StreamCodec().encode(message))
        self.assertEqual(decoded['body']['frame']['commands'], [list(c) for c in expected])

    def test_dirty_painters_wait_for_presentation_not_dom_snapshots(self):
        self.measure()
        frame = deepcopy(self.frame())
        for color in (0xff0000, 0x0000ff, 0x00ff00):
            self.runtime.app.color = color
            self.runtime.app.sync()
            self.assertEqual(self.frame(), frame)
            self.assertEqual(self.runtime.app.paints, 1)
        self.assertTrue(self.ack(frame))
        second = self.frame()
        self.assertEqual(second['commands'][4][5], '#00ff00')
        self.assertEqual(self.runtime.app.paints, 2)
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

    def test_measurements_and_active_painter_requirement_remain_checked(self):
        for bad in ({'dpr': 0}, {'width': True}, {'width': 1e6}, {'width': 4096, 'height': 4096, 'dpr': 2}):
            with self.subTest(bad=bad), self.assertRaises(ProtocolError):
                self.measure(**bad)
        self.measure()
        self.runtime.app.canvas.painter = lambda c: c.drawEllipse(0, 0, -1, 1)
        self.assertEqual(self.frame()['commands'][0][3], -1)
        with self.assertRaises(RuntimeError):
            self.runtime.app.canvas.drawLine(0, 0, 1, 1)

    def test_serializable_bad_arguments_reach_the_browser(self):
        self.measure()
        def paint(canvas):
            canvas.drawEllipse('bad x', float('nan'), -1, float('inf'), fill='invalid color')
            canvas.drawText(2 ** 60, 0, 'bad anchor', anchor='missing')
            canvas.drawRect(0, 0, 10, 10, fill=0xff0000)
        self.runtime.app.canvas.painter = paint
        state = self.runtime.snapshot(copy=False)
        stream = RenderStream()
        stream.offer(state, processed_seq=0, copy=False, trusted=True)
        message = dict(v=1, type='render', session='test', seq=1, body=stream.next_render(copy=False))
        result = StreamCodec().decode(StreamCodec().encode(message))
        commands = result['body']['canvases'][0]['commands']
        self.assertEqual(commands[0][1], 'bad x')
        self.assertTrue(math.isnan(commands[0][2]))
        self.assertEqual(commands[0][4], float('inf'))
        self.assertEqual(commands[1][9], 'missing')
        self.assertEqual(commands[2][5], '#ff0000')
        # Incoming events retain their strict value checks, even if mislabeled as render.
        with self.assertRaises(ProtocolError):
            Codec().encode(message)
        with self.assertRaises(ProtocolError):
            StreamCodec().encode(dict(message, seq=2 ** 60))

    def test_command_limit_accepts_300000_and_rejects_the_next_command(self):
        self.measure()
        node = self.runtime.app.canvas
        count = 300000
        def paint(canvas):
            # Compact valid commands fit the aggregate item budget too.
            for _ in range(count):
                canvas.drawPolyline([], color=0)
        node.painter = paint
        state = self.runtime.snapshot(copy=False)
        frame = state['canvases'][0]
        self.assertEqual(len(frame['commands']), 300000)
        message = dict(v=1, type='render', session='capacity', seq=1, body={
            'mode': 'snapshot', 'base_rev': None, 'rev': 1, 'processed_seq': 1, **state})
        decoded = StreamCodec().decode(StreamCodec().encode(message))
        self.assertEqual(decoded['body']['canvases'][0]['commands'],
                         [list(command) for command in frame['commands']])
        self.ack(frame)
        count += 1
        node.drawing.dirty = True
        with self.assertRaisesRegex(ValueError, 'Canvas frame exceeds 300000 commands'):
            self.runtime.snapshot(copy=False)
        self.assertIs(node.drawing.frame, frame)
        self.assertIsNone(node._commands)

    def test_command_limit_does_not_replace_aggregate_item_limit(self):
        self.measure()
        def paint(canvas):
            for _ in range(300000):
                canvas.drawPolyline([(0, 0)] * 5, color=0)
        self.runtime.app.canvas.painter = paint
        state = self.runtime.snapshot(copy=False)
        stream = RenderStream()
        stream.offer(state, processed_seq=0, copy=False, trusted=True)
        packet = StreamCodec().encode(dict(v=1, type='render', session='test', seq=1,
                                           body=stream.next_render(copy=False)))
        with self.assertRaisesRegex(ProtocolError, 'Value count exceeds limit'):
            StreamCodec().decode(packet)

    def test_pointer_data_raw_wheel_units_and_stale_handlers(self):
        calls = []
        node = self.runtime.app.canvas
        node.mousedown(lambda e: calls.append(e.__dict__))
        node.mouseup(lambda e: calls.append(e.__dict__))
        node.wheel(lambda e: calls.append(e.__dict__))
        node.click(lambda e: calls.append(e.__dict__))
        self.runtime.snapshot()
        def event(name, data):
            return {'node_id': node.ui.id, 'event': name, 'token': node.ui.events[name],
                    'observed_render_rev': 1, 'data': data}
        pointer = dict(x=1.5, y=-2, button=2, buttons=2, modifiers=9, pointer_id=3, cancelled=False)
        old = event('mousedown', pointer)
        self.assertEqual(self.runtime.action('event', old)[0], 'processed')
        self.assertEqual(calls[-1], pointer)
        self.assertEqual(self.runtime.action('event', event('mouseup', dict(pointer, buttons=0, cancelled=True)))[0], 'processed')
        self.assertTrue(calls[-1]['cancelled'])
        for mode in ('pixel', 'line', 'page'):
            wheel = dict(x=1, y=2, delta_x=3, delta_y=-4, delta_mode=mode, modifiers=4)
            self.assertEqual(self.runtime.action('event', event('wheel', wheel))[0], 'processed')
            self.assertEqual((calls[-1]['x_delta'], calls[-1]['y_delta']), (-3, 4) if mode == 'pixel' else (0, 0))
            self.assertEqual((calls[-1]['h_delta'], calls[-1]['v_delta']), (0, 0))
            self.assertEqual(calls[-1]['delta_mode'], mode)
        self.assertEqual(self.runtime.action('event', event('click', {}))[0], 'invalid')
        self.assertEqual(self.runtime.action('event', event('mousedown', dict(pointer, button=3)))[0], 'invalid')
        node._onMouseDown = None
        self.runtime.snapshot()
        self.assertEqual(self.runtime.action('event', old)[0], 'stale')
        self.runtime.app.show = False
        self.runtime.app.sync()
        self.runtime.snapshot()
        self.assertEqual(self.runtime.action('event', old)[0], 'stale')

    def test_shapely_geometry_collection_holes_and_empty_shapes(self):
        try:
            from shapely.geometry import GeometryCollection, Point, Polygon, LineString
        except ImportError:
            self.skipTest('Optional cookbook Shapely dependency is not installed')
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], holes=[[(2, 2), (4, 2), (4, 4), (2, 4)]])
        collection = GeometryCollection([polygon, Point(8, 8), LineString([(0, 0), (1, 1)]), Polygon()])
        self.runtime.app.canvas.painter = lambda c: c.drawShapely(collection, fill=0, stroke=0xff0000, width=2)
        self.measure()
        commands = self.frame()['commands']
        self.assertEqual([c[0] for c in commands], ['path', 'ellipse', 'polyline'])
        self.assertEqual(commands[0][2], 'evenodd')
        self.assertEqual(len(commands[0][1]), 2)
        self.assertTrue(all(p['closed'] for p in commands[0][1]))
        self.assertEqual(commands[1][3], 1)
