"""env/bin/python -m unittest discover -s tests -p textual_regression.py -v"""
import contextlib
import io
import unittest
from unittest.mock import patch

from PUI.textual import Application, Window, PUIView, HBox, VBox, Label, Button, Checkbox, RadioButton, TextField, MaskedField, DummyBinding, State


class TextualRegression(unittest.IsolatedAsyncioTestCase):
    async def test_linear_layout_centers_native_child_group(self):
        for box_type in (HBox, VBox):
            with self.subTest(box=box_type.__name__):
                class Example(Application):
                    def content(self):
                        with Window():
                            with box_type():
                                Button('Short')
                                Button('A considerably longer button label')

                root = Example()
                async with root.ui.run_test(size=(90, 30)) as pilot:
                    await pilot.pause()
                    box = root.children[0].children[0]
                    native = box.ui
                    children = [child.ui for child in box.children]
                    for width, height in ((70, 20), (80, 24)):
                        root.redraw()
                        await pilot.pause()
                        box = root.children[0].children[0]
                        self.assertIs(box.ui, native)
                        self.assertEqual([child.ui for child in box.children], children)
                        # Public native dimensions provide room around the group;
                        # PUI's general terminal dimension API is still deferred.
                        native.styles.width, native.styles.height = width, height
                        await pilot.pause()
                        regions = [child.region for child in children]
                        if box_type is HBox:
                            start, end = min(r.y for r in regions), max(r.bottom for r in regions)
                            target = native.content_region.y + native.content_region.height / 2
                            self.assertEqual(native.styles.align_vertical, 'middle')
                        else:
                            start, end = min(r.x for r in regions), max(r.right for r in regions)
                            target = native.content_region.x + native.content_region.width / 2
                            self.assertEqual(native.styles.align_horizontal, 'left')
                            self.assertTrue(all(r.x == native.content_region.x for r in regions))
                            continue
                        self.assertLessEqual(abs((start + end) / 2 - target), 1)

    async def test_application_title_is_set_without_terminal_output_in_headless_mode(self):
        class Example(Application):
            def content(self):
                with Window():
                    Label('Title')
        root = Example(title='Application title')
        with patch.object(root.ui._title_console, 'set_window_title') as set_title:
            async with root.ui.run_test() as pilot:
                await pilot.pause()
                self.assertEqual(root.ui.title, 'Application title')
                set_title.assert_not_called()

    async def test_placeholder_updates_preserve_edit_buffer_and_signals(self):
        await self.check_textfield(TextField)

    async def test_maskedfield_preserves_binding_and_edit_buffer(self):
        await self.check_textfield(MaskedField)

    async def check_textfield(self, field_type):
        model, edit = DummyBinding(''), DummyBinding('')
        events = []

        class Example(Application):
            options = {'placeholder': 'Enter text'}
            def content(self):
                with Window():
                    field_type(model, edit, **self.options).input(lambda e: events.append(('input', e.value))).change(lambda e: events.append(('change', e.value)))

        root = Example()
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            async with root.ui.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                native = root.children[0].children[0].ui
                self.assertEqual(native.password, field_type is MaskedField)
                self.assertEqual(native.placeholder, 'Enter text')
                self.assertEqual((native.value, model.value, edit.value), ('', '', ''))
                self.assertEqual(events, [])
                await pilot.click(native)
                await pilot.press('x')
                await pilot.pause()
                for options in ({'placeholder': 'Updated'}, {'placeholder': ''}, {'placeholder': None}, {}):
                    root.options = options
                    root.redraw()
                    await pilot.pause()
                    self.assertIs(root.children[0].children[0].ui, native)
                    self.assertEqual(native.password, field_type is MaskedField)
                    self.assertEqual(native.placeholder, options.get('placeholder') or '')
                    self.assertEqual((native.value, model.value, edit.value), ('x', '', 'x'))
                    self.assertEqual(events, [('input', 'x')])
                await pilot.press('enter')
                await pilot.pause()
                self.assertEqual(model.value, 'x')
                self.assertEqual(events, [('input', 'x'), ('change', 'x')])
                for value in ('programmatic', ''):
                    model.value = value
                    root.redraw()
                    await pilot.pause()
                    self.assertEqual((native.value, edit.value), (value, value))
                    self.assertEqual(events, [('input', 'x'), ('change', 'x')])
                await pilot.press('y')
                await pilot.pause()
                self.assertEqual((native.value, model.value, edit.value), ('y', '', 'y'))
                self.assertEqual(events[-1], ('input', 'y'))
        self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())

    async def test_disabled_button_retains_widget_and_blocks_activation(self):
        clicks = []

        class Example(Application):
            options = {'disabled': True}
            def content(self):
                with Window():
                    Button('Run', **self.options).click(lambda e: clicks.append('click'))

        root = Example()
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            async with root.ui.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                native = root.children[0].children[0].ui
                expected_clicks = 0
                for options in ({'disabled': True}, {'disabled': False}, {'disabled': True}, {}):
                    root.options = options
                    root.redraw()
                    await pilot.pause()
                    button = root.children[0].children[0]
                    enabled = not options.get('disabled', False)
                    self.assertIs(button.ui, native)
                    self.assertEqual(native.disabled, not enabled)
                    await pilot.click(native)
                    await pilot.pause(native.active_effect_duration)
                    expected_clicks += enabled
                    self.assertEqual(len(clicks), expected_clicks)
                    native.focus()
                    await pilot.press('enter')
                    await pilot.pause(native.active_effect_duration)
                    expected_clicks += enabled
                    self.assertEqual(len(clicks), expected_clicks)
        self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())

    async def test_disabled_selection_retains_widgets_and_blocks_clicks(self):
        flag, choice = DummyBinding(True), DummyBinding('one')

        class Example(Application):
            options = {'disabled': True}
            def content(self):
                with Window():
                    with VBox():
                        Checkbox('Check', flag, **self.options)
                        RadioButton('Radio', 'two', choice, **self.options)

        root = Example()
        async with root.ui.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            native = [node.ui for node in root.children[0].children[0].children]
            for options in ({'disabled': True}, {'disabled': False}, {'disabled': True}, {}):
                flag.value, choice.value = True, 'one'
                root.options = options
                root.redraw()
                await pilot.pause()
                controls = root.children[0].children[0].children
                enabled = not options.get('disabled', False)
                for node, ui in zip(controls, native):
                    self.assertIs(node.ui, ui)
                    self.assertEqual(ui.disabled, not enabled)
                self.assertTrue(native[0].value)
                self.assertFalse(native[1].value)
                for ui in native:
                    await pilot.click(ui)
                    await pilot.pause()
                self.assertEqual(flag.value, not enabled)
                self.assertEqual(choice.value, 'two' if enabled else 'one')

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
