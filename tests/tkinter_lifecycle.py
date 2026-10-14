"""Native Tk window/application shutdown checks; requires a display."""
import contextlib
import io
import tkinter as tk
import unittest
from unittest.mock import patch

from PUI import State, TimelineView
from PUI.dom import recur_delete
from PUI.tkinter import Application, Window, PUIView, Label, Table, TableNode


class TkLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.app = None
        self.errors = []
        self.output = io.StringIO()
        self.stdout = contextlib.redirect_stdout(self.output)
        self.stdout.__enter__()

    def tearDown(self):
        if self.app is not None and not self.app.destroyed:
            recur_delete(self.app, self.app, True)
        self.stdout.__exit__(None, None, None)
        self.assertEqual(self.errors, [])
        self.assertNotIn('<ERROR', self.output.getvalue(), self.output.getvalue())

    def mount(self, app):
        self.app = app
        app.sync()
        self.native = app.ui
        self.native.report_callback_exception = lambda *error: self.errors.append(error)
        self.native.update()

    def close(self, window):
        command = window.ui.protocol('WM_DELETE_WINDOW')
        self.assertTrue(command)
        window.ui.tk.call(command)

    def run_until_closed(self):
        timed_out = []
        def timeout():
            timed_out.append(True)
            self.native.quit()
        token = self.native.after(2000, timeout)
        try:
            self.app.start()
        finally:
            self.native.after_cancel(token)
        self.assertFalse(timed_out, 'Closing the last window did not end mainloop')

    def test_last_window_close_ends_mainloop_and_cleans_up(self):
        class Child(PUIView):
            def content(self):
                with TimelineView(60):
                    Label('timer')
        class Example(Application):
            def content(self):
                with Window():
                    Child()
        self.mount(Example())
        window = self.app.children[0]
        child = window.children[0]
        timeline = child.children[0]
        timer = timeline.timer
        def close():
            self.close(window)
            child.redraw()  # Pending work must be canceled during teardown.
        self.native.after(0, close)
        self.run_until_closed()
        self.assertTrue(self.app.destroyed)
        self.assertTrue(window.destroyed)
        self.assertTrue(child.destroyed)
        self.assertIsNone(child._after_id)
        self.assertIsNone(timeline.timer)
        self.assertTrue(timer.finished.is_set())
        self.assertEqual(self.app._windows, set())

    def test_other_windows_survive_close_and_redraw(self):
        class Child(PUIView):
            def content(self):
                with Window().id('nested'):
                    Label('second')
        class Example(Application):
            def content(self):
                with Window().id('first'):
                    Label('first')
                Child()
        self.mount(Example())
        first = self.app.children[0]
        second = self.app.children[1].children[0]
        first_ui, second_ui = first.ui, second.ui
        # Destroying a child widget must not count as closing its window.
        probe = tk.Label(first_ui, text='temporary native child')
        probe.destroy()
        self.native.update()
        self.assertEqual(self.app._windows, {first_ui, second_ui})
        self.close(first)
        self.native.update()
        self.assertFalse(self.app.destroyed)
        self.assertEqual(first_ui.state(), 'withdrawn')
        self.assertEqual(self.app._windows, {second_ui})
        self.app.sync()
        self.native.update()
        self.assertIs(self.app.children[0].ui, first_ui)
        self.assertEqual(first_ui.state(), 'withdrawn')
        self.native.after(0, lambda: self.close(second))
        self.run_until_closed()
        self.assertTrue(self.app.destroyed)

    def test_replacing_last_window_does_not_quit_but_removing_it_does(self):
        class Example(Application):
            window_key = 'first'
            def content(self):
                if self.window_key:
                    with Window().id(self.window_key):
                        Label(self.window_key)
        self.mount(Example())
        original = self.app.children[0].ui
        self.app.window_key = 'replacement'
        self.app.sync()
        self.native.update()
        replacement = self.app.children[0].ui
        self.assertIsNot(original, replacement)
        self.assertFalse(self.app.destroyed)
        self.assertEqual(self.app._windows, {replacement})
        def remove():
            self.app.window_key = None
            self.app.sync()
        self.native.after(0, remove)
        self.run_until_closed()
        self.assertTrue(self.app.destroyed)

    def test_last_close_cancels_table_dialog_and_repeated_quit(self):
        state = State()
        state.value = 'value'
        class Example(Application):
            def content(self):
                with Window():
                    with Table():
                        with TableNode():
                            TableNode(state('value'))
        self.mount(Example())
        window = self.app.children[0]
        table = window.children[0]
        table._edit(table._cell(0, 0))
        editor = table.editor
        self.native.update()
        def close():
            self.close(window)
            self.app.quit()
            token = self.app._quit_id
            self.app.quit()
            self.assertEqual(self.app._quit_id, token)
        self.native.after(0, close)
        self.run_until_closed()
        self.assertTrue(editor.closed)
        self.assertFalse(self.native.tk.call('info', 'commands', str(editor.dialog)))
        self.assertIsNone(self.app._quit_id)
        self.assertIsNone(self.app._window_check_id)

    def test_mainloop_exception_still_cleans_up(self):
        class Example(Application):
            def content(self):
                with Window():
                    Label('value')
        self.mount(Example())
        with patch.object(self.native, 'mainloop', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.app.start()
        self.assertTrue(self.app.destroyed)


if __name__ == '__main__':
    unittest.main()
