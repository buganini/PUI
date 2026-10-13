"""env/bin/python -m unittest discover -s tests -p textual_tabs.py -v"""
import unittest
import PUI.textual as backend
import textual_views
from tabs_async_cases import TabsAsyncCases


class TextualTabsTests(TabsAsyncCases, unittest.IsolatedAsyncioTestCase):
    backend = backend
    asyncSetUp = textual_views.TextualViewsTests.asyncSetUp

    async def mount(self, root):
        self.root = root
        self.context = root.ui.run_test(size=(100, 32))
        self.pilot = await self.context.__aenter__()
        await self.pump()

    async def asyncTearDown(self):
        if hasattr(self, 'context'):
            await self.context.__aexit__(None, None, None)
        await textual_views.TextualViewsTests.asyncTearDown(self)

    async def pump(self):
        await self.pilot.pause()

    def selected_index(self):
        tabs = self.tabs()
        current = tabs.frame.visible_content
        self.assertEqual(tabs.bar.active, current.id if current is not None else '')
        return next((i for i, page in enumerate(tabs.children) if page.ui is current), None)

    async def native_select(self, index):
        tab = self.tabs().bar.get_tab(self.tabs().children[index].ui.id)
        await self.pilot.click(tab)
        await self.pump()

    def tab_label(self, index):
        return self.tabs().bar.get_tab(self.tabs().children[index].ui.id).label.plain
