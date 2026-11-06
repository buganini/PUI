"""Cookbook tiles fill cells without making ordinary labels expandable."""
import os
os.environ['PUI_BACKEND'] = 'wx'
import unittest
from PUI.cookbook.adaptive_grid import AdaptiveGridExample
from PUI.expansion import priority
from PUI.dom import recur_delete

class AdaptiveGridTiles(unittest.TestCase):
    def test_tiles_keep_expansion_with_minimum_dimensions(self):
        import wx
        from PUI.wx import Application, Window
        app = wx.GetApp() or wx.App()
        class Demo(Application):
            def content(self):
                with Window(size=(900, 800)):
                    AdaptiveGridExample()
        root = Demo()
        try:
            root.sync()
            root.children[0].ui.Show()
            for _ in range(5):
                app.Yield()
                app.ProcessPendingEvents()
            def walk(node):
                yield node
                for child in node.children:
                    yield from walk(child)
            tiles = {n._id: n for n in walk(root) if n._id and n._id in 'ABCDEFG'}
            self.assertEqual(len(tiles), 7)
            for tile in tiles.values():
                self.assertIsInstance(tile.outer, wx.Panel)
                from PUI.wx.base import int_to_wx_colour
                self.assertEqual(tile.outer.GetBackgroundColour(), int_to_wx_colour(tile.style_bgcolor))
                self.assertIs(tile.children[0].ui.GetParent(), tile.outer)
                self.assertGreater(tile.outer.GetSize().width, 40)
                self.assertGreater(priority(tile, 'x'), 0)
                self.assertGreater(priority(tile, 'y'), 0)
                self.assertIsNone(tile.layout_height)
                self.assertGreater(tile.layout_minHeight, 0)
                self.assertEqual(priority(tile.children[0], 'x'), 0)
                self.assertEqual(priority(tile.children[0], 'y'), 0)
        finally:
            recur_delete(root, root, True)

    def test_panel_survives_background_changes(self):
        import wx
        from PUI.wx import Application, Window, VBox, Label
        from PUI.wx.base import int_to_wx_colour
        app = wx.GetApp() or wx.App()
        class Demo(Application):
            color = None
            def content(self):
                with Window(size=(400, 300)):
                    with VBox().style(bgColor=self.color) as self.box:
                        self.label = Label('Retained')
        root = Demo()
        try:
            root.sync()
            panel, label = root.box.outer, root.label.ui
            for color in (0x244B5A, 0xA84A3A, None):
                root.color = color
                root.sync()
                app.Yield()
                self.assertIs(root.box.outer, panel)
                self.assertIs(root.label.ui, label)
                self.assertIs(label.GetParent(), panel)
                if color is not None:
                    self.assertEqual(panel.GetBackgroundColour(), int_to_wx_colour(color))
        finally:
            recur_delete(root, root, True)
