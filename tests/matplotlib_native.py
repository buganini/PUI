"""Run with PUI_TEST_BACKEND=wx or tkinter in separate GUI processes."""
import importlib
import os
import unittest


class NativeMatplotlib(unittest.TestCase):
    def test_native_canvas_retention_events_resize_and_removal(self):
        from PUI.expansion import priority
        backend = os.environ.get('PUI_TEST_BACKEND', 'wx')
        pui = importlib.import_module('PUI.' + backend)

        class Demo(pui.Application):
            show = True
            version = 1

            def content(self):
                with pui.Window().layout(width=700, height=500):
                    with pui.VBox():
                        if self.show:
                            self.chart = pui.MatplotlibCanvas(self.plot, self.version)

            def plot(self, figure, version):
                from matplotlib.patches import Circle
                figure.clear()
                ax = figure.subplots()
                ax.plot([0, 1], [0, version], linestyle='--')
                text = ax.text(.5, .5, r'$x^2$', rotation=30, clip_on=True)
                text.set_clip_path(Circle((.5, .5), .4, transform=ax.transData))

        app = Demo()
        try:
            app.sync()
            def pump():
                if backend == 'wx':
                    app.ui.Yield()
                else:
                    app.ui.update()
            pump()
            chart = app.chart
            canvas, figure, ui = chart.figure_canvas, chart.figure, chart.ui
            expected = 'FigureCanvasWxAgg' if backend == 'wx' else 'FigureCanvasTkAgg'
            self.assertEqual(type(canvas).__name__, expected)
            canvas.draw()
            self.assertGreater(canvas.buffer_rgba().nbytes, 0)
            self.assertEqual((priority(chart, 'x'), priority(chart, 'y')), (4, 4))
            events = []
            canvas.mpl_connect('button_press_event', events.append)
            canvas.mpl_connect('key_press_event', events.append)
            if backend == 'wx':
                import wx
                event = wx.MouseEvent(wx.wxEVT_LEFT_DOWN)
                event.SetPosition((80, 60))
                ui.GetEventHandler().ProcessEvent(event)
                key = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
                key.SetKeyCode(ord('a'))
                ui.GetEventHandler().ProcessEvent(key)
                ui.SetSize((460, 320))
            else:
                ui.event_generate('<ButtonPress-1>', x=80, y=60)
                ui.focus_force()
                pump()
                ui.event_generate('<KeyPress-a>')
                ui.configure(width=460, height=320)
            pump()
            self.assertEqual([e.name for e in events], ['button_press_event', 'key_press_event'])
            self.assertEqual(events[0].button.value, 1)
            self.assertEqual(events[1].key, 'a')
            self.assertEqual(tuple(map(round, figure.bbox.size)), canvas.get_width_height(physical=True))
            app.version = 2
            app.sync(); pump()
            self.assertIs(app.chart.figure_canvas, canvas)
            self.assertIs(app.chart.figure, figure)
            self.assertIs(app.chart.ui, ui)
            self.assertEqual(figure.axes[0].lines[0].get_ydata()[-1], 2)
            app.chart.layout(width=240, height=180)
            self.assertEqual((priority(app.chart, 'x'), priority(app.chart, 'y')), (0, 0))
            canvas.draw_idle()
            app.show = False
            app.sync(); pump()
            if backend == 'tkinter':
                self.assertIsNone(canvas._idle_draw_id)
                self.assertFalse(ui.winfo_exists())
            else:
                self.assertFalse(ui)
        finally:
            if backend == 'wx' and hasattr(app, 'chart'):
                widget = app.chart.ui
                if widget and widget.HasCapture():
                    widget.ReleaseMouse()
            app.quit()


if __name__ == '__main__':
    unittest.main()
