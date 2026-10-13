"""QT_QPA_PLATFORM=offscreen env/bin/python -m unittest discover -s tests -p pyside6_tabs.py -v"""
import unittest
import PUI.PySide6 as backend
from PySide6 import QtCore, QtTest
import pyside6_views
from tabs_native_cases import TabsNativeCases


class PySideTabsTests(TabsNativeCases, unittest.TestCase):
    backend = backend
    setUpClass = classmethod(pyside6_views.PySideViewsTests.setUpClass.__func__)
    setUp = pyside6_views.PySideViewsTests.setUp
    tearDown = pyside6_views.PySideViewsTests.tearDown
    sync = pyside6_views.PySideViewsTests.sync
    mount = pyside6_views.PySideViewsTests.mount

    def pump(self):
        self.app.processEvents()

    def selected_index(self):
        index = self.tabs().ui.currentIndex()
        return None if index < 0 else index

    def native_select(self, index):
        bar = self.tabs().ui.tabBar()
        QtTest.QTest.mouseClick(bar, QtCore.Qt.MouseButton.LeftButton,
                               pos=bar.tabRect(index).center())

    def tab_label(self, index):
        return self.tabs().ui.tabText(index)

    def test_native_selection_after_redraw_and_receiver_collection(self):
        import gc
        state = backend.State()
        state.selection = 'alpha'
        self.create(state('selection'))  # Deliberately do not retain old nodes.
        for index, key in [(1, 'Beta'), (0, 'alpha')] * 4:
            self.sync()
            gc.collect()
            self.native_select(index)
            self.pump()
            self.assertEqual(state.selection, key)
            self.sync()
            self.assertEqual(self.selected_index(), index)

    def test_redraw_preserves_external_selection_listener(self):
        seen = []
        self.create()
        self.tabs().ui.currentChanged.connect(seen.append)
        self.sync()
        self.native_select(1)
        self.pump()
        self.assertEqual(seen, [1])
