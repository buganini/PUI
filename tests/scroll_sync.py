import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from PUI.PySide6.layout import VBox
from PUI.PySide6.scroll import Scroll


class ScrollSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_offsets_exist_before_range_signals_and_are_transferred(self):
        old = Scroll(horizontal=True)
        old.update(None)
        old.ui.horizontalScrollBar().setRange(0, 100)
        old.ui.verticalScrollBar().setRange(0, 100)
        old.ui.horizontalScrollBar().setValue(23)
        old.ui.verticalScrollBar().setValue(37)
        old.preSync()

        new = Scroll(horizontal=True)
        new.update(old)

        self.assertEqual(new.hsb_offset, 23)
        self.assertEqual(new.vsb_offset, 37)

    def test_resize_during_sync_uses_retained_qt_widget(self):
        old = Scroll()
        old.update(None)
        mounted_child = VBox()
        mounted_child.update(None)
        old.addChild(0, mounted_child)

        new = Scroll()
        new.ui = old.ui
        new.children = [VBox()]
        old.retired_by = new

        event = QtGui.QResizeEvent(
            QtCore.QSize(20, 20),
            QtCore.QSize(10, 10),
        )
        old.onUiResized(event)

    def test_horizontal_range_handler_updates_horizontal_bar(self):
        scroll = Scroll(horizontal=True)
        scroll.update(None)
        scroll.ui.horizontalScrollBar().setRange(0, 100)
        scroll.hsb_offset = 19
        scroll.align_x = 0
        scroll.hsb_range_changed(0, 100)

        self.assertEqual(scroll.ui.horizontalScrollBar().value(), 19)
        self.assertEqual(scroll.ui.verticalScrollBar().value(), 0)


if __name__ == "__main__":
    unittest.main()
