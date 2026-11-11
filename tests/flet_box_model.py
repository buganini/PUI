import unittest
from PUI import State
import PUI.flet as UI
import flet_regression


class FletBoxModel(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = flet_regression.FletRegression.asyncSetUp
    asyncTearDown = flet_regression.FletRegression.asyncTearDown
    mount = flet_regression.FletRegression.mount
    sync = flet_regression.FletRegression.sync

    async def test_native_content_padding(self):
        state=State(); state.text='Text'
        class App(UI.Application):
            padding=12
            def content(self):
                with UI.Window():
                    with UI.VBox().layout(padding=self.padding) as self.box:
                        self.field=UI.TextField(state('text')).layout(padding=self.padding, margin=7)
                        self.edit=UI.TextEdit(state('text')).layout(padding=self.padding)
                        self.button=UI.Button('Button').layout(padding=self.padding)
        await self.mount(App())
        field=self.root.field.ui
        for padding in (12, 0, None):
            self.root.padding=padding
            self.sync()
            self.assertEqual(self.root.box.shell.padding.left, 11 if padding is None else padding)
            self.assertIs(self.root.field.ui, field)
            self.assertIsNone(self.root.field.shell.padding)
            self.assertIsNone(self.root.button.shell.padding)
            self.assertEqual(self.root.field.shell.margin.left, 7)
            for actual in (self.root.field.ui.content_padding,
                           self.root.edit.ui.content_padding,
                           self.root.button.ui.style.padding):
                if padding is None: self.assertIsNone(actual)
                else: self.assertEqual(actual.left, padding)
