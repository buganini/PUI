"""Native wx non-blocking Modal lifecycle (GUI required)."""
import unittest
import wx
from PUI import wx as UI
from PUI.dom import recur_delete
from tests.modal import demo


class WxModal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = wx.GetApp() or wx.App()

    def pump(self):
        for _ in range(3):
            self.native.Yield()

    def tearDown(self):
        recur_delete(self.root, self.root, bool(self.root.children[0].ui))
        self.pump()
        self.assertFalse(self.native._pui_modal_windows.stack)
        self.assertFalse(self.native._pui_modal_windows.disabled)

    def test_retention_close_and_removal(self):
        self.root = root = demo(UI)
        root.sync(); self.pump()
        owner = root.children[0].ui
        self.assertFalse(root.modal.ui.IsShown())
        root.state.open = True; root.sync(); self.pump()
        dialog, label = root.modal.ui, root.label.ui
        self.assertTrue(dialog.IsShown())
        self.assertFalse(dialog.IsModal())  # Show(), no nested event loop.
        self.assertFalse(owner.IsEnabled())
        root.version = 'two'; root.sync(); self.pump()
        self.assertIs(root.label.ui, label)
        dialog.Close(); self.pump()
        self.assertFalse(root.state.open)
        self.assertTrue(owner.IsEnabled())
        self.assertEqual(root.events, ['open', 'close'])
        root.state.open = True; root.sync(); self.pump()
        root.show = False; root.sync(); self.pump()
        self.assertFalse(dialog)
        self.assertTrue(owner.IsEnabled())
        self.assertEqual(root.events, ['open', 'close', 'open', 'close'])

    def test_parent_destroy_restores_other_windows(self):
        self.root = root = demo(UI)
        root.sync(); self.pump()
        other = wx.Frame(None)
        other.Show()
        try:
            root.state.open = True; root.sync(); self.pump()
            self.assertFalse(other.IsEnabled())
            root.children[0].ui.Destroy()
            self.pump()
            self.assertTrue(other.IsEnabled())
            self.assertEqual(root.events, ['open', 'close'])
        finally:
            other.Destroy()

    def test_nested_restore_and_pre_disabled_window(self):
        class Demo(UI.Application):
            def setup(self):
                self.state = UI.State()
                self.state.a = False
                self.state.b = True
                self.state.text = 'content'
            def content(self):
                with UI.Window() as self.window:
                    with UI.VBox():
                        UI.Label('Background')
                        with UI.Modal(self.state('a'), offValue=False) as self.a:
                            with UI.VBox():
                                UI.TextField(self.state('text'))
                                with UI.Modal(self.state('b'), offValue=False) as self.b:
                                    UI.Button('Inner')
        self.root = root = Demo()
        root.sync(); self.pump()
        other = wx.Frame(None)
        other.Show(); other.Enable(False)
        try:
            root.state.a = True; root.sync(); self.pump()
            self.assertFalse(root.window.ui.IsEnabled())
            self.assertFalse(root.a.ui.IsEnabled())
            self.assertTrue(root.b.ui.IsEnabled())
            event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
            event.KeyCode = wx.WXK_ESCAPE
            root.b.ui.GetEventHandler().ProcessEvent(event)
            self.pump()
            self.assertFalse(root.state.b)
            self.assertTrue(root.a.ui.IsEnabled())
            root.state.b = True; root.sync(); self.pump()
            root.state.a = False; root.sync(); self.pump()
            self.assertFalse(root.a.ui.IsShown())
            self.assertFalse(root.b.ui.IsShown())
            self.assertTrue(root.state.b)
            self.assertTrue(root.window.ui.IsEnabled())
            self.assertFalse(other.IsEnabled())
            root.state.a = True; root.sync(); self.pump()
            self.assertTrue(root.b.ui.IsShown())
            self.assertFalse(root.a.ui.IsEnabled())
        finally:
            other.Destroy()
