"""env/bin/python -m unittest discover -s tests -p flet_canvas.py -v"""
import asyncio
import contextlib
import io
import unittest
from types import SimpleNamespace

import flet as ft
from flet.messaging.session import Session
from flet_regression import RecordingConnection
from PUI.dom import recur_delete
from PUI.flet import Application, Window, Canvas, MouseButton


def position(x=20.5, y=30.25):
    return {'l': {'x': x, 'y': y}, 'g': {'x': x + 300, 'y': y + 400}}


def pointer(x=20.5, y=30.25):
    return dict(position(x, y), k='mouse', ts={'microseconds': 100}, dev=0,
                ps=0, pMin=0, pMax=1, dist=0, distMax=0, size=0,
                rMj=0, rMn=0, rMin=0, rMax=0, **{'or': 0, 'tilt': 0})


class FletCanvasTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connection = RecordingConnection(asyncio.get_running_loop())
        self.session = Session(self.connection)
        self.root = None
        self.events = []
        self.enabled = True
        self.version = 0
        self.visible = True

    async def asyncTearDown(self):
        if self.root is not None:
            recur_delete(self.root, self.root, True)
        await asyncio.sleep(0)

    async def mount(self):
        owner = self
        class Example(Application):
            def content(self):
                with Window():
                    if owner.visible:
                        canvas = Canvas(lambda c: c.drawRect(0, 0, c.width, c.height, fill=0)).layout(weight=1)
                        if owner.enabled:
                            for name in ('mousedown', 'mouseup', 'mousemove', 'mouseenter',
                                         'mouseleave', 'dblclick', 'wheel'):
                                getattr(canvas, name)(owner.record, name, owner.version)
        self.root = Example()
        await self.root.flet_app(self.session.page)

    def record(self, event, name, version):
        self.events.append((name, version, vars(event)))

    @property
    def canvas(self):
        return self.root.children[0].children[0]

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.root.sync()
        self.assertNotIn('<ERROR', output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())

    async def event(self, name, payload=None, gesture=None):
        gesture = gesture or self.canvas.gesture
        with self.assertNoLogs('flet', level='ERROR'):
            await self.session.dispatch_event(gesture._i, name, payload)
            await asyncio.sleep(0)

    async def test_hover_enter_exit_and_canvas_sizing_survive_wrapper(self):
        await self.mount()
        canvas = self.canvas
        self.assertIsInstance(canvas.gesture, ft.GestureDetector)
        self.assertIs(canvas.outer.content, canvas.gesture)
        self.assertIs(canvas.gesture.content, canvas.ui)
        self.assertTrue(canvas.gesture.expand)
        self.assertTrue(canvas.ui.expand)
        await self.event('enter', pointer())
        await self.event('hover', pointer(15, 35))
        await self.event('exit', pointer(-1, 80))
        self.assertEqual([event[0] for event in self.events], ['mouseenter', 'mousemove', 'mouseleave'])
        self.assertEqual(self.events[1][2], {'x': 15, 'y': 35, 'button': MouseButton.NONE})
        canvas.on_resize(SimpleNamespace(width=400, height=300))
        self.assertEqual(len(canvas.ui.shapes), 1)
        self.assertEqual((canvas.ui.shapes[0].width, canvas.ui.shapes[0].height), (400, 300))

    async def test_primary_tap_and_drag_release_outside_after_redraw(self):
        await self.mount()
        gesture = self.canvas.gesture
        await self.event('pan_down', position())
        await self.event('pan_cancel')  # the tap recognizer wins
        self.assertEqual([event[0] for event in self.events], ['mousedown'])
        await self.event('tap_up', position(22, 34))
        self.assertFalse(self.events[-1][2]['cancelled'])
        self.events.clear()
        await self.event('pan_down', position(10, 10))
        await self.event('tap_cancel')  # the pan recognizer wins
        await self.event('pan_start', dict(position(15, 15), k='mouse'))
        await self.event('pan_update', position(-50, 450))
        self.version = 2
        self.sync()
        self.assertIs(self.canvas.gesture, gesture)
        await self.event('pan_end', dict(position(-55, 460), v={'x': 0, 'y': 0}))
        self.assertEqual([event[0] for event in self.events],
                         ['mousedown', 'mousemove', 'mousemove', 'mouseup'])
        self.assertEqual(self.events[-1], ('mouseup', 2, dict(x=-55, y=460,
                         button=MouseButton.LEFT, cancelled=False)))
        self.assertEqual(self.canvas._input_state['pressed'], {})

    async def test_right_drag_middle_tap_and_middle_cancel(self):
        await self.mount()
        await self.event('right_pan_start', pointer())
        await self.event('right_pan_update', pointer(70, 80))
        await self.event('right_pan_end', pointer(90, 100))
        self.assertEqual([event[2]['button'] for event in self.events], [MouseButton.RIGHT] * 3)
        self.events.clear()
        await self.event('tertiary_tap_down', position())
        await self.event('tertiary_tap_up', position(21, 31))
        await self.event('tertiary_tap_down', position(50, 60))
        await self.event('tertiary_tap_cancel')
        self.assertEqual(self.events[-1][2], dict(x=50, y=60, button=MouseButton.MIDDLE, cancelled=True))

    async def test_double_recognition_and_primary_cancellation_are_distinct(self):
        await self.mount()
        await self.event('double_tap_down', position())
        await self.event('double_tap_cancel')
        self.assertEqual(self.events, [])
        await self.event('pan_down', position(1, 2))
        await self.event('tap_cancel')
        await self.event('pan_cancel')
        self.assertEqual(self.events[-1][2], dict(x=1, y=2, button=MouseButton.LEFT, cancelled=True))
        await self.event('double_tap_down', position(20, 30))
        self.version = 3
        self.sync()
        await self.event('double_tap')
        self.assertEqual(self.events[-1], ('dblclick', 3, dict(x=20, y=30, button=MouseButton.LEFT)))
        self.assertEqual(len(self.events), 3)

    async def test_scroll_reports_pixels_without_fabricating_angles_or_modifiers(self):
        await self.mount()
        await self.event('scroll', dict(position(), sd={'x': -2.5, 'y': 40}))
        self.assertEqual(self.events, [('wheel', 0, dict(x=20.5, y=30.25,
                         button=MouseButton.NONE, x_delta=2.5, y_delta=-40,
                         h_delta=0, v_delta=0, modifiers=None))])

    async def test_native_double_tap_consumes_tap_up_without_leaving_pressed_state(self):
        await self.mount()
        await self.event('pan_down', position(10, 20))
        await self.event('pan_cancel')
        await self.event('pan_down', position(10, 20))
        await self.event('double_tap_down', position(10, 20))
        await self.event('pan_cancel')
        await self.event('double_tap')
        self.assertEqual([event[0] for event in self.events],
                         ['mousedown', 'mouseup', 'mousedown', 'mouseup', 'dblclick'])
        self.assertTrue(self.events[1][2]['cancelled'])
        self.assertTrue(self.events[3][2]['cancelled'])
        self.assertEqual(self.canvas._input_state['pressed'], {})

    async def test_current_callbacks_removed_handlers_and_destroyed_events(self):
        await self.mount()
        canvas, gesture = self.canvas, self.canvas.gesture
        old_hover = gesture.on_hover
        old_down = gesture.on_pan_down
        self.version = 4
        self.sync()
        await old_hover(SimpleNamespace(local_position=ft.Offset(1, 2)))
        self.assertEqual(self.events[-1][1], 4)
        self.enabled = False
        self.sync()
        self.assertIs(self.canvas.outer.content, self.canvas.ui)
        for name in ('hover', 'enter', 'exit', 'pan_down', 'pan_end', 'tap_up',
                     'right_pan_start', 'tertiary_tap_down', 'double_tap', 'scroll'):
            self.assertIsNone(getattr(gesture, 'on_' + name))
        await old_hover(SimpleNamespace(local_position=ft.Offset(3, 4)))
        await old_down(SimpleNamespace(local_position=ft.Offset(3, 4)))
        self.assertEqual(self.canvas._input_state['pressed'], {})
        self.assertEqual(len(self.events), 1)
        self.enabled = True
        self.sync()
        self.assertIs(self.canvas.outer.content, gesture)
        old_down = gesture.on_pan_down
        self.visible = False
        self.sync()
        await old_down(SimpleNamespace(local_position=ft.Offset(5, 6)))
        await old_hover(SimpleNamespace(local_position=ft.Offset(5, 6)))
        canvas.on_resize(SimpleNamespace(width=500, height=500))
        self.assertEqual(len(self.events), 1)


if __name__ == '__main__':
    unittest.main()
