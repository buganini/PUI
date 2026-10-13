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
