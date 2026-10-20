"""Textual autocomplete integration and focus checks (headless Pilot)."""
import unittest
import PUI.textual as UI


class Demo(UI.Application):
    def __init__(self):
        super().__init__()
        self.state = UI.State()
        self.state.value = ''
        self.disabled = False
        self.autoexpand = True
        self.changes = []

    def content(self):
        with UI.Window():
            with UI.VBox():
                with UI.ComboBox(editable=True, text_model=self.state('value'),
                                 disabled=self.disabled, autoexpand=self.autoexpand).change(lambda e:self.changes.append(e.value)) as self.combo:
                    UI.ComboBoxItem('Amsterdam', 'AMS')
                    UI.ComboBoxItem('Taipei Taoyuan', 'TPE')
                    UI.ComboBoxItem('Taipei Songshan', 'TSA')
                    UI.ComboBoxItem('Tokyo Haneda', 'HND')
                    UI.ComboBoxItem('Tokyo Narita', 'NRT')
                UI.TextField(UI.DummyBinding('next'))
                UI.Label(self.state.value)


class TextualComboBoxTests(unittest.IsolatedAsyncioTestCase):
    async def test_typing_keyboard_focus_and_binding(self):
        root = Demo()
        async with root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            combo = root.combo.ui
            combo.editor.focus()
            await pilot.press(*'tai tok')
            await pilot.pause()
            self.assertEqual(combo.editor.value, 'tai tok')
            self.assertEqual(root.state.value, 'tai tok')
            self.assertEqual(combo.indices, [0,1,2,3,4])
            self.assertTrue(combo.choices.display)
            self.assertIs(root.ui.focused, combo.editor)
            await pilot.press('down','down','down','down','enter')
            await pilot.pause()
            self.assertEqual(root.state.value, 'HND')
            self.assertEqual(combo.editor.value, 'Tokyo Haneda')
            self.assertEqual(root.changes, [3])
            self.assertIs(root.ui.focused, combo.editor)
            await pilot.press('x','escape')
            self.assertFalse(combo.choices.display)
            await pilot.press('backspace','tab')
            await pilot.pause()
            self.assertFalse(combo.choices.display)
            self.assertIsNot(root.ui.focused, combo.editor)
            self.assertIs(root.combo.ui, combo)

    async def test_disabled_and_autocomplete_toggle(self):
        root = Demo()
        async with root.ui.run_test() as pilot:
            await pilot.pause()
            combo=root.combo.ui
            combo.editor.focus()
            await pilot.press('t')
            root.autoexpand=False;root.redraw();await pilot.pause()
            self.assertFalse(combo.choices.display)
            await pilot.press('o');self.assertEqual(combo.editor.value,'to')
            root.autoexpand=True;root.redraw();await pilot.pause()
            await pilot.press('k');await pilot.pause()
            self.assertEqual(combo.indices,[0,1,2,3,4])
            root.disabled=True;root.redraw();await pilot.pause()
            self.assertFalse(combo.choices.display)
            self.assertTrue(combo.disabled)

    async def test_mouse_selection_and_external_updates(self):
        root = Demo()
        async with root.ui.run_test(size=(100,30)) as pilot:
            await pilot.pause()
            combo=root.combo.ui
            combo.editor.focus()
            await pilot.press(*'han')
            await pilot.pause()
            self.assertEqual(combo.indices,[0,1,2,3,4])
            await pilot.click(combo.choices,offset=(2,1))
            await pilot.pause()
            self.assertEqual(root.state.value,'AMS')
            self.assertIs(root.ui.focused,combo.editor)
            await pilot.press('end','x')
            self.assertEqual(combo.editor.value,'Amsterdamx')
            root.state.value='AMS';await pilot.pause()
            self.assertEqual(combo.editor.value,'Amsterdam')

    async def test_noneditable_and_full_choices_when_completion_disabled(self):
        root=Demo()
        root.autoexpand=False
        async with root.ui.run_test() as pilot:
            await pilot.pause()
            combo=root.combo.ui
            combo.editor.focus()
            await pilot.press('z','down')
            await pilot.pause()
            self.assertEqual(combo.indices,[0,1,2,3,4])
            await pilot.press('enter');await pilot.pause()
            self.assertEqual(root.state.value,'AMS')
        class Readonly(UI.Application):
            def content(self):
                with UI.Window():
                    with UI.ComboBox(text_model=model) as self.combo:
                        UI.ComboBoxItem('One','1')
                        UI.ComboBoxItem('Two','2')
        model=UI.DummyBinding('1');root=Readonly()
        async with root.ui.run_test() as pilot:
            await pilot.pause()
            select=root.combo.ui.select
            self.assertEqual(select.value,0)
            select.value=1;await pilot.pause()
            self.assertEqual(model.value,'2')
