"""env/bin/python -m unittest discover -s tests -p textual_regression.py -v"""
import contextlib
import io
import unittest

from PUI.textual import Application, Window, PUIView, HBox, VBox, Label, TextField, DummyBinding, State


class TextualRegression(unittest.IsolatedAsyncioTestCase):
    async def test_textfield_expands_horizontally_at_native_height(self):
        class Example(Application):
            def content(self):
                with Window():
                    with HBox():
                        TextField(DummyBinding('value'))

        root = Example()
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            async with root.ui.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                field = root.children[0].children[0].children[0]
                self.assertEqual(field.expand_x_prio, 3)
                self.assertEqual(str(field.ui.styles.width), '1fr')
                self.assertEqual(str(field.ui.styles.height), 'auto')
        self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())

    async def test_buffered_textfield_does_not_redraw_during_mount(self):
        state = State()
        state.text = 'initial'
        state.editing = ''

        class Editor(PUIView):
            def content(self):
                with VBox():
                    Label('State:' + state.text)
                    TextField(state('text'))
                    Label('Editing:' + state.editing)
                    TextField(state('text'), state('editing'))

        class Example(Application):
            def content(self):
                with Window():
                    Editor()

        root = Example()
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            async with root.ui.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                fields = list(root.ui.query('Input'))
                self.assertEqual(len(fields), 2)
                self.assertEqual(state.editing, 'initial')
                await pilot.click(fields[1])
                await pilot.press('end', 'x')
                await pilot.pause()
                self.assertEqual(state.editing, 'initialx')
                self.assertEqual(state.text, 'initial')
        self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())


if __name__ == '__main__':
    unittest.main()
