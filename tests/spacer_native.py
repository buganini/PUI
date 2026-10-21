"""Native spacers share the main axis with explicitly weighted siblings."""
import contextlib
import importlib
import io
import unittest

from PUI.dom import recur_delete


class SpacerTests(unittest.TestCase):
    def exercise(self, backend):
        UI = importlib.import_module('PUI.' + backend)
        if backend == 'PySide6':
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance() or QApplication([])
            type(self)._qt_app = app
        else:
            import wx
            app = wx.GetApp() or wx.App(False)
            type(self)._wx_app = app

        for horizontal in (False, True):
            box_type = UI.HBox if horizontal else UI.VBox
            class Demo(UI.Application):
                inverse = False
                spacer_weight = 1
                show_spacer = True
                def content(self):
                    with UI.Window(size=(640, 480)):
                        with box_type(inverse=self.inverse).layout(padding=0) as self.box:
                            with box_type().layout(weight=1, padding=0) as self.content_box:
                                UI.Label('Row 1')
                                UI.Divider()
                                UI.Label('Row 2')
                            self.spacer = UI.Spacer().visible(self.show_spacer)
                            if self.spacer_weight != 1:
                                self.spacer.layout(weight=self.spacer_weight)
            root = Demo()
            root.ui = app
            def sync():
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    root.sync()
                    for _ in range(3):
                        if backend == 'PySide6':
                            app.processEvents()
                        else:
                            root.children[0].ui.Layout()
                            wx.YieldIfNeeded()
                self.assertNotIn('<ERROR', output.getvalue())
            def extent(node):
                if backend == 'PySide6':
                    size = node.ui.geometry().size()
                    return size.width() if horizontal else size.height()
                item = next(item for child, item in root.box.sizerItems
                            if child.get_node() is node)
                size = item.GetSize()
                return size.width if horizontal else size.height
            try:
                sync()
                native = root.content_box.ui
                for weight, visible, inverse in ((1, True, False), (1, True, True),
                                                  (2, True, False), (1, False, False),
                                                  (1, True, False)):
                    with self.subTest(backend=backend, horizontal=horizontal,
                                      weight=weight, visible=visible, inverse=inverse):
                        root.spacer_weight, root.show_spacer, root.inverse = weight, visible, inverse
                        sync()
                        self.assertIs(root.content_box.ui, native)
                        for row in (root.content_box.children[0], root.content_box.children[-1]):
                            if backend == 'PySide6':
                                self.assertEqual(row.ui.size(), row.ui.sizeHint())
                            else:
                                self.assertEqual(row.ui.GetSize(), row.ui.GetBestSize())
                        content, spacer = extent(root.content_box), extent(root.spacer)
                        if visible:
                            self.assertGreater(spacer, 50)
                            self.assertAlmostEqual(spacer, content * weight, delta=3)
                        else:
                            self.assertGreater(content, 350)
            finally:
                root.ui = None  # The suite owns the shared native application.
                recur_delete(root, root, True)
                if backend == 'PySide6':
                    app.processEvents()
                else:
                    wx.YieldIfNeeded()

    def test_pyside6(self):
        self.exercise('PySide6')

    def test_wx(self):
        self.exercise('wx')
