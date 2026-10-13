"""/usr/bin/python3 -m unittest discover -s tests -p wx_tabs.py -v (GUI required)."""
import unittest
import PUI.wx as backend
import wx_views
from tabs_native_cases import TabsNativeCases


class WxTabsTests(TabsNativeCases, unittest.TestCase):
    backend = backend
    setUpClass = classmethod(wx_views.WxViewsTests.setUpClass.__func__)
    setUp = wx_views.WxViewsTests.setUp
    tearDown = wx_views.WxViewsTests.tearDown
    sync = wx_views.WxViewsTests.sync
    mount = wx_views.WxViewsTests.mount
    pump = wx_views.WxViewsTests.pump

    def selected_index(self):
        index = self.tabs().ui.GetSelection()
        return None if index < 0 else index

    def native_select(self, index):
        self.tabs().ui.SetSelection(index)

    def tab_label(self, index):
        return self.tabs().ui.GetPageText(index)
