"""Run with a Tk-enabled Python and display: python3 -m unittest discover -s tests -p tkinter_regression.py"""
import importlib.util
import unittest
from unittest.mock import patch

available = importlib.util.find_spec('tkinter') is not None
if available:
    from PUI.tkinter import PUI, Application, Window, VBox, Label, TextField, DummyBinding, Tabs, Tab, Scroll, Canvas, ComboBox, ComboBoxItem
    from PUI.dom import recur_delete


@unittest.skipUnless(available, 'tkinter is not installed')
class TkinterRegression(unittest.TestCase):
    def wait_for(self, predicate):
        import time
        deadline = time.monotonic() + 1
        while not predicate() and time.monotonic() < deadline:
            self.root.ui.update()
            time.sleep(0.005)
        self.assertTrue(predicate())

    def tearDown(self):
        if hasattr(self, 'root'):
            recur_delete(self.root, self.root, True)

    def test_edit_payloads_and_programmatic_changes(self):
        model, edit = DummyBinding('initial'), DummyBinding('')
        events = []
        class Example(Application):
            def content(self):
                with Window():
                    with VBox():
                        TextField(model, edit).input(lambda e: events.append(('input', e.value))).change(lambda e: events.append(('change', e.value)))
        self.root = Example()
        self.root.sync()
        native_root = self.root.ui
        model.value = 'programmatic'
        self.root.sync()
        self.assertIs(self.root.ui, native_root)
        field = self.root.children[0].children[0].children[0]
        self.assertEqual(events, [])
        field.variable.set('typed')
        self.root.sync()
        field = self.root.children[0].children[0].children[0]
        field.on_change()
        field.on_change()
        self.assertEqual(model.value, 'typed')
        self.assertEqual(events, [('input', 'typed'), ('change', 'typed')])
        self.assertEqual(len(field.variable.trace_info()), 1)

    def test_redraw_coalesces_through_native_parent(self):
        self.root = Application()
        self.root.sync()
        with patch.object(self.root.ui, 'after_idle') as after:
            for _ in range(1000):
                self.root.redraw()
        self.assertEqual(after.call_count, 1)

    def test_initial_window_flags_and_tabs_removal(self):
        class Example(Application):
            flags = True
            tabs = True
            def content(self):
                with Window(fullscreen=self.flags):
                    if self.tabs:
                        with Tabs():
                            with Tab('page'):
                                Label('inside')
                    else:
                        Label('replacement')
        self.root = Example()
        self.root.sync()
        self.root.ui.update()
        self.root.flags = False
        self.root.sync()
        self.root.ui.update()
        window = self.root.children[0]
        self.wait_for(lambda: bool(window.ui.attributes('-fullscreen')))
        window.fullscreen(False)
        self.root.ui.update()
        self.wait_for(lambda: not bool(window.ui.attributes('-fullscreen')))
        self.root.tabs = False
        self.root.sync()

    def test_scroll_mount_and_empty_bounds(self):
        class Example(Application):
            def content(self):
                with Window(size=(300, 180)):
                    with Scroll().scrollY(Scroll.END):
                        with VBox():
                            Label('content')
        self.root = Example()
        self.root.sync()
        scroll = self.root.children[0].children[0]
        self.assertIs(scroll.outer, scroll.ui.container)
        with patch.object(scroll.ui.canvas, 'bbox', return_value=None):
            scroll.ui.update_scroller()
            scroll.preSync()
        self.assertFalse(scroll.ui.wheel_bindings == {})

    def test_canvas_shapes_and_text_signature(self):
        def painter(canvas):
            canvas.drawText(0, 0, 'text', size=12, color=0, rotate=15)
            canvas.drawRect(30, 30, 10, 10, fill=0xFF0000)
            canvas.drawEllipse(50, 50, 5, 10, stroke=0)
            canvas.drawPolygon([(0, 0), (5, 0), (5, 5)], fill=0)
        class Example(Application):
            def content(self):
                with Window():
                    Canvas(painter).layout(width=100, height=100)
        self.root = Example()
        self.root.sync()
        canvas = self.root.children[0].children[0]
        items = canvas.ui.find_all()
        self.assertEqual(len(items), 4)
        self.assertEqual(canvas.ui.coords(items[1]), [10.0, 10.0, 30.0, 30.0])

    def test_removed_subview_cancels_native_idle_callback(self):
        @PUI
        def Child():
            Label('child')
        class Example(Application):
            show = True
            def content(self):
                with Window():
                    with VBox():
                        if self.show:
                            Child()
        self.root = Example()
        self.root.sync()
        child = self.root.children[0].children[0].children[0]
        child.redraw()
        token = child._after_id
        self.assertIn(token, self.root.ui.tk.call('after', 'info'))
        self.root.show = False
        self.root.sync()
        self.assertNotIn(token, self.root.ui.tk.call('after', 'info'))
        self.root.ui.update()

    def test_combobox_selection_free_text_and_reuse(self):
        index, text = DummyBinding(0), DummyBinding('one')
        events = []
        class Example(Application):
            def content(self):
                with Window():
                    with ComboBox(editable=True, index_model=index, text_model=text).change(lambda e: events.append(e.value)):
                        ComboBoxItem('first', 'one')
                        ComboBoxItem('second', 'two')
        self.root = Example()
        self.root.sync()
        combo = self.root.children[0].children[0]
        combo.ui.current(1)
        combo.ui.event_generate('<<ComboboxSelected>>')
        self.root.ui.update_idletasks()
        self.assertEqual(text.value, 'two')
        self.assertEqual(events, [1])
        combo.variable.set('typed')
        self.root.ui.update_idletasks()
        self.root.sync()
        combo = self.root.children[0].children[0]
        self.assertEqual(index.value, -1)
        self.assertEqual(combo.variable.get(), 'typed')
        self.assertEqual(len(combo.variable.trace_info()), 1)
