import unittest
import PUI.textual as UI


class TextualFontTests(unittest.IsolatedAsyncioTestCase):
    async def test_select(self):
        class App(UI.Application):
            def __init__(self):
                super().__init__()
                self.state = UI.State({'font': 'Alpha'})
            def content(self):
                with UI.Window():
                    self.picker = UI.FontComboBox(self.state('font'), fonts=['Alpha', 'Beta'])
        app = App()
        async with app.ui.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            select = app.picker.ui.select
            select.value = 1
            await pilot.pause()
            self.assertEqual(app.state['font'], 'Beta')
            app.state['font'] = 'Alpha'
            await pilot.pause()
            self.assertEqual(app.picker.ui.select.value, 0)
