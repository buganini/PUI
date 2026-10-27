import time
import unittest
from PUI import tkinter as UI
from PUI.dom import recur_delete
from tests.modal import demo


class TkModal(unittest.TestCase):
    def pump(self):
        for _ in range(5):
            self.app.ui.update()
            time.sleep(.01)

    def tearDown(self):
        self.app.quit()

    def test_retained_content_dismiss_reopen_and_remove(self):
        self.app=demo(UI);self.app.sync();self.pump()
        self.assertFalse(self.app.modal.ui.winfo_viewable())
        self.app.state.open=True;self.app.sync();self.pump()
        ui=self.app.modal.ui;label=self.app.label.ui
        self.assertIs(ui.grab_current(),ui)
        self.app.version='two';self.app.sync();self.pump()
        self.assertIs(self.app.label.ui,label)
        ui.event_generate('<Escape>');self.pump()
        self.assertFalse(self.app.state.open)
        self.assertIsNone(ui.grab_current())
        self.assertEqual(self.app.events,['open','close'])
        self.app.state.open=True;self.app.sync();self.pump()
        self.app.show=False;self.app.sync();self.pump()
        self.assertFalse(ui.winfo_exists())
        self.assertIsNone(self.app.ui.grab_current())
        self.assertEqual(self.app.events,['open','close','open','close'])

    def test_nested_grab_and_parent_close(self):
        class Demo(UI.Application):
            def __init__(self):
                super().__init__();self.state=UI.State();self.state.outer=False;self.state.inner=False
            def content(self):
                with UI.Window():
                    with UI.VBox():
                        UI.Label('outside')
                        with UI.Modal(self.state('outer'),offValue=False) as self.outer_modal:
                            with UI.VBox():
                                UI.Label('outer')
                                with UI.Modal(self.state('inner'),offValue=False) as self.inner_modal:
                                    UI.Label('inner')
        self.app=Demo();self.app.sync();self.pump()
        self.app.state.outer=True;self.app.sync();self.pump()
        outer=self.app.outer_modal.ui
        self.app.state.inner=True;self.app.sync();self.pump()
        self.assertIs(self.app.ui.grab_current(),self.app.inner_modal.ui)
        self.app.inner_modal._dismiss();self.pump()
        self.assertIs(self.app.ui.grab_current(),outer)
        self.app.state.inner=True;self.app.sync();self.pump()
        self.app.state.outer=False;self.app.sync();self.pump()
        self.assertFalse(self.app.inner_modal.ui.winfo_viewable())
        self.assertIsNone(self.app.ui.grab_current())
