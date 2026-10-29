"""Qt rejection must synchronize state even when closeEvent is bypassed."""
import unittest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PUI import PySide6 as UI
from PUI.dom import recur_delete
from tests.modal import demo


class QtModalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = QApplication.instance() or QApplication([])

    def setUp(self):
        self.app = demo(UI)
        self.app.ui = self.native
        self.app.sync()

    def tearDown(self):
        self.app.ui = None
        recur_delete(self.app, self.app, True)
        self.native.processEvents()

    def test_escape_reject_close_and_reopen(self):
        dialog = self.app.modal.ui
        for dismiss in (lambda: QTest.keyClick(dialog, Qt.Key.Key_Escape), dialog.reject, dialog.close):
            with self.subTest(dismiss=dismiss):
                self.app.events.clear()
                self.app.state.open = True
                self.app.sync()
                self.assertTrue(dialog.isVisible())
                # Force a declarative update: the connection must use the new node.
                old = self.app.modal
                self.app.version += '!'
                self.app.sync()
                self.assertIsNot(old, self.app.modal)
                self.assertIs(dialog, self.app.modal.ui)
                dismiss()
                self.native.processEvents()
                self.assertFalse(self.app.state.open)
                self.assertFalse(dialog.isVisible())
                self.assertEqual(self.app.events, ['open', 'close'])
                self.app.state.open = True
                self.app.sync()
                self.assertTrue(dialog.isVisible())
                self.app.state.open = False
                self.app.sync()
                self.assertFalse(dialog.isVisible())
                self.assertEqual(self.app.events, ['open', 'close', 'open', 'close'])

if __name__ == '__main__': unittest.main()
