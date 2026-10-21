"""PUI_BACKEND=textual env/bin/python -m unittest discover -s tests -p textual_cookbook.py"""
import contextlib
import io
import os
import unittest
from unittest.mock import patch


class CookbookLayoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_wide_overrides_repaint_when_example_pane_resizes(self):
        with patch.dict(os.environ, {'PUI_BACKEND': 'textual'}):
            from PUI.cookbook.app import Cookbook

        def walk(node):
            yield node
            for child in node.children:
                yield from walk(child)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            root = Cookbook()
            async with root.ui.run_test(size=(120, 45)) as pilot:
                retained = None

                def check(wide):
                    nonlocal retained
                    label = next(node for node in walk(root)
                                 if getattr(node, 'text', None) == 'Wide layout/style overrides')
                    self.assertEqual(label.parent._state.size[0] >= 60, wide)
                    if retained is None:
                        retained = (label.ui, label.widget)
                    self.assertEqual((label.ui, label.widget), retained)
                    self.assertEqual(tuple(label.ui.styles.padding), (1 if wide else 0,) * 4)
                    self.assertEqual(label.widget.region.x - label.ui.region.x, int(wide))
                    self.assertEqual(label.widget.region.y - label.ui.region.y, int(wide))
                    self.assertEqual(label.ui.region.height, 3 if wide else 1)
                    segment = next(s for s in label.widget.render_line(0) if s.text.strip())
                    color = 0x1C2A30 if wide else 0xFFF7E6
                    self.assertEqual(segment.style.color.get_truecolor(),
                                     (color >> 16, color >> 8 & 255, color & 255))
                    self.assertEqual(bool(segment.style.bold), wide)

                for width in (120, 160, 200, 120):
                    await pilot.resize_terminal(width, 45)
                    await pilot.pause()
                    check(width >= 160)

                # The breakpoint follows the pane, even without terminal resize.
                splitter = root.children[0].children[0].children[1].ui
                handle = splitter.handles[0]
                for delta, wide in [(-20, True), (20, False), (-20, True)]:
                    destination = (handle.region.x + delta, handle.region.y)
                    await pilot.mouse_down(handle)
                    await pilot.hover(offset=destination)
                    await pilot.mouse_up(offset=destination)
                    await pilot.pause()
                    check(wide)
        self.assertNotIn('<ERROR', output.getvalue())

    async def test_compact_menu_and_retained_panes_when_resizing_and_switching_pages(self):
        with patch.dict(os.environ, {'PUI_BACKEND': 'textual'}):
            from PUI.cookbook.app import Cookbook, pages
        root = Cookbook()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            async with root.ui.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                box = root.children[0].children[0]
                panes = [box.children[0], *box.children[1].children]
                retained = [pane.ui for pane in panes]
                for width, page in [(120, 'Button'), (80, 'TextField'), (120, 'Combobox'), (120, 'Adaptive Layout'), (160, 'HBox'), (160, 'Vbox'), (160, 'Grid'), (160, 'Adaptive Grid'), (120, 'Splitter')]:
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
                    if page == 'Combobox':
                        from PUI.textual.combobox import _Combo
                        combo = next(
                            control for control in root.ui.query(_Combo)
                            if control.puinode.editable and not control.disabled
                            and control.puinode.autoexpand
                        )
                        combo.editor.scroll_visible(animate=False)
                        combo.editor.focus()
                        await pilot.press(*'tai tok')
                        await pilot.pause()
                        self.assertEqual(combo.indices, [0, 1, 2, 3])
                        self.assertIs(root.ui.focused, combo.editor)
                        await pilot.press('down', 'enter')
                        await pilot.pause()
                        self.assertEqual(combo.editor.value, 'Taipei Taoyuan (TPE)')
                        self.assertEqual(combo.puinode.text_model.value, 'TPE')
                        clear = next(
                            button for button in root.ui.query('Button')
                            if str(button.label) == 'Clear autocomplete'
                        )
                        clear.scroll_visible(animate=False)
                        await pilot.pause()
                        await pilot.click(clear)
                        await pilot.pause()
                        self.assertEqual(combo.editor.value, '')
                        self.assertEqual(combo.puinode.text_model.value, '')
                    box = root.children[0].children[0]
                    panes = [box.children[0], *box.children[1].children]
                    if page in ('Adaptive Layout', 'HBox', 'Vbox'):
                        from textual.widgets import Rule
                        rules = list(panes[-1].ui.query(Rule))
                        self.assertEqual(len(rules), {'Adaptive Layout': 3, 'HBox': 3, 'Vbox': 1}[page])
                        vertical = page == 'HBox'
                        for rule in rules:
                            self.assertEqual(rule.orientation, 'vertical' if vertical else 'horizontal')
                            self.assertGreater(rule.region.width, 0)
                            self.assertGreater(rule.region.height, 0)
                            self.assertIn('│' if vertical else '─', rule.render_line(0).text)
                    self.assertEqual([pane.ui for pane in panes], retained)
                    self.assertLess(box.children[0].ui.region.width, width // 3)
                    for pane in panes:
                        region = pane.ui.region
                        self.assertGreater(region.width, 1)
                        self.assertGreater(region.height, 1)
                        self.assertGreaterEqual(region.x, 0)
                        self.assertGreaterEqual(region.y, 0)
                        self.assertLessEqual(region.right, width)
                        self.assertLessEqual(region.bottom, 40)
        self.assertNotIn('<ERROR', output.getvalue())
