"""env/bin/python -m unittest discover -s tests -p tkinter_tabs.py -v (GUI required)."""
import unittest
import PUI.tkinter as backend
import tkinter_views
from tabs_native_cases import TabsNativeCases


class TkTabsTests(TabsNativeCases, unittest.TestCase):
    backend = backend
    setUp = tkinter_views.TkViewsTests.setUp
    tearDown = tkinter_views.TkViewsTests.tearDown
    sync = tkinter_views.TkViewsTests.sync
    mount = tkinter_views.TkViewsTests.mount
    pump = tkinter_views.TkViewsTests.pump

    def selected_index(self):
        selected = self.tabs().ui.select()
        return self.tabs().ui.index(selected) if selected else None

    def native_select(self, index):
        self.tabs().ui.select(index)

    def tab_label(self, index):
        return self.tabs().ui.tab(index, 'text')
