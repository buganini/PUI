"""Run with a Tk-enabled Python and display: python3 -m unittest discover -s tests -p tkinter_regression.py"""
import importlib.util
import unittest
from unittest.mock import patch

available = importlib.util.find_spec('tkinter') is not None
if available:
    from PUI.tkinter import Application, Window, VBox, Label, TextField, DummyBinding, Tabs, Tab
    from PUI.dom import recur_delete


@unittest.skipUnless(available, 'tkinter is not installed')
class TkinterRegression(unittest.TestCase):
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
        self.root.flags = False
        self.root.sync()
        window = self.root.children[0]
        self.assertTrue(bool(window.ui.attributes('-fullscreen')))
        window.fullscreen(False)
        self.assertFalse(bool(window.ui.attributes('-fullscreen')))
        self.root.tabs = False
        self.root.sync()
