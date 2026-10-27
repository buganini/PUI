"""Matplotlib callbacks through the validated browser protocol and Flet controls."""
import asyncio
import unittest
from types import SimpleNamespace
from PUI.web import Application, Window, MatplotlibCanvas
from PUI.web.runtime import Runtime


class BrowserEvents(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        class Demo(Application):
            plots = 0
            def content(self):
                with Window():
                    self.chart = MatplotlibCanvas(self.plot)
            def plot(self, figure):
                self.plots += 1
                figure.clear()
                figure.subplots().plot([0, 1], [0, 1], picker=20)
        self.runtime = Runtime(asyncio.get_running_loop())
        self.addCleanup(self.runtime.close)
        self.app = self.runtime.app = Demo()
        self.app.sync(); self.runtime.snapshot()
        self.node = self.app.chart
        self.runtime.canvas_control('measure', dict(node_id=self.node.ui.id, measure_rev=1,
            width=600, height=400, dpr=2, visible=True))
        frame = self.runtime.snapshot()['canvases'][0]
        self.runtime.canvas_control('canvas_ack', {k: frame[k] for k in ('node_id','measure_rev','frame_rev')} | {'status':'drawn'})
        self.canvas = self.node.figure_canvas
        self.events = []
        for name in ('button_press_event', 'button_release_event', 'motion_notify_event',
                     'scroll_event', 'key_press_event', 'key_release_event',
                     'figure_enter_event', 'figure_leave_event', 'pick_event'):
            self.canvas.mpl_connect(name, self.events.append)

    def send(self, name, **data):
        if name in ('keydown', 'keyup'):
            payload = dict(key='a', modifiers=0)
        elif name == 'blur':
            payload = dict(cancelled=True)
        elif name == 'wheel':
            payload = dict(x=200, y=100, delta_x=0, delta_y=-100, delta_mode='pixel', modifiers=0)
        else:
            payload = dict(x=200, y=100, button=1, buttons=1, modifiers=0, pointer_id=1, cancelled=False)
        payload.update(data)
        return self.runtime.action('event', dict(node_id=self.node.ui.id, event=name,
            token=self.node.ui.events[name], observed_render_rev=0, data=payload))

    def test_coordinates_buttons_wheel_keys_and_cleanup(self):
        self.assertEqual(self.send('mousedown', button=4, buttons=4, dblclick=True), ('processed',None))
        e = self.events[-1]
        self.assertEqual((e.x,e.y,e.button.value,e.dblclick), (200,300,2,True))
        self.send('mousemove', button=0, buttons=5, modifiers=3)
        self.assertEqual({b.value for b in self.events[-1].buttons}, {1,2})
        self.assertEqual(set(self.events[-1].modifiers), {'shift','ctrl'})
        self.send('wheel')
        self.assertEqual((self.events[-1].step,self.events[-1].button), (1,'up'))
        self.send('wheel', delta_mode='line',delta_y=2)
        self.assertEqual(self.events[-1].step,-2)
        self.send('keydown',key='ArrowLeft',modifiers=2)
        self.assertEqual(self.events[-1].key,'ctrl+left')
        self.send('keyup',key='ArrowLeft')
        self.assertEqual(self.events[-1].key,'ctrl+left')
        self.send('keydown',key='A',code='KeyA',modifiers=1)
        self.send('keyup',key='a',code='KeyA')
        self.assertEqual(self.events[-1].key,'A')
        self.assertFalse(self.canvas.input_events.keys)
        self.send('keydown',key='Shift',modifiers=1)
        self.send('blur')
        self.assertFalse(self.canvas.input_events.keys)
        self.assertFalse(self.canvas.input_events.buttons)
        self.assertEqual(self.events[-1].name,'key_release_event')
        self.assertEqual(self.app.plots,1)

    def test_pick_reconciliation_and_reconnect(self):
        x,y = self.canvas.figure.axes[0].transData.transform((.5,.5))
        self.send('mousedown', x=float(x), y=float(400-y))
        self.assertTrue(any(e.name=='pick_event' for e in self.events))
        self.app.sync(); self.runtime.snapshot(); self.node=self.app.chart
        self.assertIs(self.node.figure_canvas,self.canvas)
        self.events.clear()
        self.send('keydown')
        self.assertEqual(len(self.events),1)
        self.runtime.reset_connection()
        self.assertFalse(self.canvas.input_events.keys)
        self.assertFalse(self.canvas.input_events.buttons)

    def test_native_navigation_controller_can_pan_and_zoom(self):
        from matplotlib.backend_bases import NavigationToolbar2
        toolbar = NavigationToolbar2(self.canvas)
        ax = self.canvas.figure.axes[0]
        original = ax.get_xlim()
        toolbar.pan()
        self.send('mousedown',x=250,y=200)
        self.send('mousemove',x=300,y=200)
        self.send('mouseup',x=300,y=200,buttons=0)
        self.assertNotEqual(ax.get_xlim(),original)
        toolbar.home()
        self.assertEqual(ax.get_xlim(),original)
        toolbar.zoom()
        self.send('mousedown',x=200,y=180)
        self.send('mousemove',x=350,y=260)
        self.send('mouseup',x=350,y=260,buttons=0)
        self.assertLess(ax.get_xlim()[1]-ax.get_xlim()[0],original[1]-original[0])
        self.assertEqual(self.app.plots,1)

    def test_invalid_keyboard_payload_is_rejected(self):
        self.assertEqual(self.send('keydown',key='a'*129)[0],'invalid')
        self.assertEqual(self.send('keyup',modifiers=16)[0],'invalid')


class FletEvents(unittest.IsolatedAsyncioTestCase):
    async def test_keyboard_gestures_and_retention(self):
        from PUI.flet import Application as FApp, Window as FWindow, MatplotlibCanvas as FCanvas
        class Demo(FApp):
            def content(self):
                with FWindow():
                    self.chart = FCanvas(lambda f: f.subplots().plot([0,1],[0,1]))
        # Control construction works without launching the Flutter client.
        from flet.messaging.session import Session
        from tests.flet_regression import RecordingConnection
        session = Session(RecordingConnection(asyncio.get_running_loop()))
        app=Demo();await app.flet_app(session.page)
        chart=app.chart
        try:
            canvas=chart.figure_canvas
            got=[]
            canvas.mpl_connect('key_press_event',got.append)
            canvas.mpl_connect('button_press_event',got.append)
            self.assertIs(chart.shell.content,chart.keyboard)
            await chart.keyboard.on_key_down(SimpleNamespace(key='Control Left'))
            await chart.keyboard.on_key_down(SimpleNamespace(key='A'))
            self.assertEqual(got[-1].key,'ctrl+a')
            chart.dispatch_pointer(SimpleNamespace(x=20,y=30),'_onMouseDown',1)
            self.assertEqual(got[-1].button.value,1)
            self.assertIn('ctrl',got[-1].modifiers)
            keyboard=chart.keyboard
            app.sync()
            self.assertIs(app.chart.keyboard,keyboard)
        finally:
            from PUI.dom import recur_delete
            recur_delete(app,app,True)
