"""Native splitter handles remain easy to grab in both orientations."""
import unittest
from PySide6 import QtCore, QtWidgets, QtTest
from PUI.PySide6 import Window, Splitter, Label
from PUI.PySide6.base import QtPUIView
from PUI.dom import recur_delete


class SplitterTests(unittest.TestCase):
    def test_handle_size_and_drag(self):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        class View(QtPUIView):
            vertical = False
            def content(self):
                with Window(size=(600, 400)):
                    with Splitter(vertical=self.vertical) as self.splitter:
                        Label('First')
                        Label('Second')
        root = View()
        try:
            for vertical in (False, True):
                root.vertical = vertical
                root.sync()
                root.children[0].ui.show()
                app.processEvents()
                splitter = root.splitter.ui
                handle = splitter.handle(1)
                extent = handle.height() if vertical else handle.width()
                self.assertGreaterEqual(extent, 8)
                before = splitter.sizes()[0]
                point = handle.rect().center()
                offset = QtCore.QPoint(0, 30) if vertical else QtCore.QPoint(30, 0)
                QtTest.QTest.mousePress(handle, QtCore.Qt.LeftButton, pos=point)
                QtTest.QTest.mouseMove(handle, point + offset)
                QtTest.QTest.mouseRelease(handle, QtCore.Qt.LeftButton, pos=point + offset)
                self.assertGreater(splitter.sizes()[0], before)
        finally:
            recur_delete(root, root, True)
            app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
