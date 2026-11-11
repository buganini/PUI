import unittest
import PUI.flet as UI
import flet_regression


class FletGap(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = flet_regression.FletRegression.asyncSetUp
    asyncTearDown = flet_regression.FletRegression.asyncTearDown
    mount = flet_regression.FletRegression.mount
    sync = flet_regression.FletRegression.sync

    async def test_spacing_updates_and_default(self):
        class App(UI.Application):
            gap=12
            def content(self):
                with UI.Window():
                    with UI.VBox() as self.box:
                        with UI.HBox(gap=self.gap,tGap=99) as self.row:
                            UI.Label('A')
                            UI.Label('B')
                        with UI.HVBox(minWidth=300,gap=self.gap) as self.adaptive:
                            UI.Label('C')
        await self.mount(App())
        self.assertEqual(self.root.box.ui.spacing,0)
        self.assertEqual(self.root.row.ui.spacing,12)
        self.assertEqual(self.root.adaptive.ui.spacing,12)
        self.root.gap=0
        self.sync()
        self.assertEqual(self.root.row.ui.spacing,0)
        self.assertEqual(self.root.adaptive.ui.spacing,0)
