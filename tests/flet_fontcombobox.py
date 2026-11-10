import unittest
from types import SimpleNamespace
import PUI.flet as UI
import flet_regression


class FletFontTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = flet_regression.FletRegression.asyncSetUp
    asyncTearDown = flet_regression.FletRegression.asyncTearDown
    mount = flet_regression.FletRegression.mount
    sync = flet_regression.FletRegression.sync

    async def test_selection(self):
        state = UI.State({'font': 'Alpha'})
        class App(UI.Application):
            def content(self):
                with UI.Window():
                    self.picker = UI.FontComboBox(state('font'), fonts=['Alpha', 'Beta'])
        await self.mount(App())
        picker = self.root.picker
        self.assertEqual([o.text for o in picker.ui.options], ['Alpha', 'Beta'])
        picker.ui.value = '1'
        picker.on_select(SimpleNamespace())
        self.assertEqual(state['font'], 'Beta')
        state['font'] = 'Alpha'
        self.sync()
        self.assertEqual(self.root.picker.ui.value, '0')
