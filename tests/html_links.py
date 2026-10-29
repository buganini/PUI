import unittest
from unittest.mock import patch
from PUI import PySide6 as UI
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PUI.dom import recur_delete

class QtHtmlLinks(unittest.TestCase):
    def test_retained_link_policy(self):
        native=QApplication.instance() or QApplication([])
        class App(UI.Application):
            enabled=False
            def content(self):
                with UI.Window():
                    self.html=UI.Html('<a href="https://example.com">link</a>',selectable=True,openURL=self.enabled)
        app=App();app.ui=native
        try:
            app.sync();widget=app.html.ui
            with patch('PUI.PySide6.text.OpenURL') as launch:
                for enabled in (False,True,True,False):
                    app.enabled=enabled;app.sync()
                    self.assertIs(widget,app.html.ui)
                    flags=widget.textInteractionFlags()
                    self.assertEqual(bool(flags & Qt.TextInteractionFlag.LinksAccessibleByMouse),enabled)
                    self.assertTrue(flags & Qt.TextInteractionFlag.TextSelectableByMouse)
                    launch.reset_mock();widget.linkActivated.emit('https://example.com')
                    self.assertEqual(launch.call_count,int(enabled))
        finally:
            app.ui=None;recur_delete(app,app,True)
