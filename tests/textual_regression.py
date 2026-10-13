"""env/bin/python -m unittest discover -s tests -p textual_regression.py -v"""
import contextlib
import io
import unittest

from PUI.textual import Application, Window, HBox, TextField, DummyBinding


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


if __name__ == '__main__':
    unittest.main()
