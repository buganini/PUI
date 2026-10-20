"""PUI_BACKEND=textual env/bin/python -m unittest discover -s tests -p textual_cookbook.py"""
import contextlib
import io
import os
import unittest
from unittest.mock import patch


class CookbookLayoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_compact_menu_and_retained_panes_when_resizing_and_switching_pages(self):
        with patch.dict(os.environ, {'PUI_BACKEND': 'textual'}):
            from PUI.cookbook.app import Cookbook, pages
        root = Cookbook()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            async with root.ui.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                panes = root.children[0].children[0].children
                retained = [pane.ui for pane in panes]
                for width, page in [(120, 'Button'), (80, 'TextField'), (120, 'Adaptive Layout')]:
                    await pilot.resize_terminal(width, 40)
                    await pilot.pause()
                    box = root.children[0].children[0]
                    menu = box.children[0].children[1].children[0]
                    label = menu.children[next(i for i, item in enumerate(pages) if item[1] == page)]
                    label.ui.scroll_visible(animate=False)
                    await pilot.pause()
                    await pilot.click(label.ui)
                    await pilot.pause()
                    self.assertEqual(root.state.page, page)
                    box = root.children[0].children[0]
                    self.assertEqual([pane.ui for pane in box.children], retained)
                    self.assertLess(box.children[0].ui.region.width, width // 3)
                    for pane in box.children:
                        region = pane.ui.region
                        self.assertGreater(region.width, 1)
                        self.assertGreater(region.height, 1)
                        self.assertGreaterEqual(region.x, 0)
                        self.assertGreaterEqual(region.y, 0)
                        self.assertLessEqual(region.right, width)
                        self.assertLessEqual(region.bottom, 40)
        self.assertNotIn('<ERROR', output.getvalue())
