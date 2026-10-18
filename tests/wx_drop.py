import unittest
import wx
import PUI.wx as UI
from PUI.wx.drop import DropTarget


class DropTests(unittest.TestCase):
    def test_target_registration_and_data_adapter(self):
        app=wx.GetApp() or wx.App()
        seen=[]
        class Example(UI.Application):
            def content(self):
                with UI.Window():
                    self.label=UI.Label('drop').drop(lambda e:(seen.append(e),e.accept()))
        root=Example();root.ui=app;root.sync()
        try:
            target=root.label.ui.GetDropTarget()
            self.assertIsInstance(target,DropTarget)
            class TextTarget(DropTarget):
                def GetData(self):return True
            target=TextTarget(root.label)
            # Exercise wx's native data objects and the format selected by negotiation.
            target.data=target.text
            target.text.SetText('hello')
            target.data.GetReceivedFormat=target.text.GetFormat
            for action in (wx.DragCopy,wx.DragMove,wx.DragLink):
                self.assertEqual(target.OnData(1,2,action),action)
            self.assertEqual([e.action for e in seen],['copy','move','link'])
            self.assertEqual(seen[-1].text,'hello')
            root.label.drop(lambda e:None)
            self.assertEqual(target.OnData(1,2,wx.DragCopy),wx.DragNone)
        finally:
            for w in wx.GetTopLevelWindows():w.Destroy()
            app.Yield()
