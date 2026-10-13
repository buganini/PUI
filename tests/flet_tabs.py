"""env/bin/python -m unittest discover -s tests -p flet_tabs.py -v"""
import asyncio
import unittest
import PUI.flet as backend
import flet_regression
from tabs_async_cases import TabsAsyncCases


class FletTabsTests(TabsAsyncCases, unittest.IsolatedAsyncioTestCase):
    backend = backend
    asyncSetUp = flet_regression.FletRegression.asyncSetUp
    asyncTearDown = flet_regression.FletRegression.asyncTearDown
    mount = flet_regression.FletRegression.mount

    async def pump(self):
        await asyncio.sleep(0)

    def selected_index(self):
        tabs = self.tabs()
        self.assertEqual(tabs.ui.visible, bool(tabs.children))
        return tabs.ui.selected_index if tabs.children else None

    async def native_select(self, index):
        native = self.tabs().ui
        await self.session.dispatch_event(native._i, 'change', index)
        await self.pump()

    def tab_label(self, index):
        return self.tabs().bar.tabs[index].label

    async def test_tab_click_updates_model_before_animation_finishes(self):
        tabs = await self.create()
        await self.session.dispatch_event(tabs.bar._i, 'click', 1)
        # The click is authoritative even before Tabs.change or a redraw.
        self.assertEqual(tabs.model.value, 'Beta')
        await self.pump()
        self.assertEqual(self.selected_index(), 1)
        await self.session.dispatch_event(self.tabs().ui._i, 'change', 1)
        await self.pump()
        self.assertEqual(self.selected_index(), 1)
