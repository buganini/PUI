"""Native WebView HTML and explicit HtmlWindow fallback (GUI required)."""
import json
import time
import unittest
import warnings
from unittest.mock import patch
import wx
import wx.html
from PUI.wx import Application, Window, Html
from PUI.dom import recur_delete


class WxHtml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.GetApp() or wx.App()
        cls.log = wx.LogStderr()
        cls.old_log = wx.Log.SetActiveTarget(cls.log)

    @classmethod
    def tearDownClass(cls):
        wx.Log.FlushActive()
        wx.Log.SetActiveTarget(cls.old_log)

    def tearDown(self):
        if hasattr(self, 'root'):
            recur_delete(self.root, self.root, True)
        self.app.Yield()

    def mount(self):
        class Demo(Application):
            text = '<span id="text" style="color:rgb(255,0,0)">HTML</span>'
            selectable = False
            open_url = False
            def content(self):
                with Window(size=(500, 350)):
                    self.html = Html(self.text, selectable=self.selectable, openURL=self.open_url).style(
                        color=0x123456, bgColor=0xFFF7E6, fontSize=18)
        self.root = Demo()
        self.root.sync()
        self.assertTrue(hasattr(self.root, 'html'))
        self.assertIsNotNone(self.root.html.ui)
        return self.root.html

    def wait_script(self, script, expected):
        deadline = time.monotonic() + 10
        last = None
        while time.monotonic() < deadline:
            self.app.Yield()
            ok, last = self.root.html.ui.RunScript('document.readyState === "complete" ? (' + script + ') : ""')
            if ok and last == expected:
                return
            time.sleep(.01)
        self.fail(f'WebView script did not reach {expected!r}: {last!r}')

    def test_links_disabled_enabled_and_retained(self):
        html = self.mount()
        if not html._webview:
            self.skipTest('Native WebView unavailable')
        self.root.text = '<a id="link" href="https://example.com">Link</a>'
        self.root.sync()
        self.wait_script('String(!!document.getElementById("link"))', 'true')
        with patch('PUI.wx.text.OpenURL') as launch:
            for enabled in (False, True, False):
                retained = self.root.html.ui
                self.root.open_url = enabled
                self.root.sync()
                self.assertIs(self.root.html.ui, retained)
                self.root.html.ui.RunScript('document.getElementById("link").click()')
                for _ in range(20):
                    self.app.Yield(); time.sleep(.01)
                self.assertEqual(launch.call_count, int(enabled))
                launch.reset_mock()
                self.assertTrue(self.root.html.ui.RunScript('String(!!document.getElementById("link"))')[0])

    def test_fallback_links(self):
        with patch.object(Html, '_create_webview', side_effect=RuntimeError('test fallback')):
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                html = self.mount()
        with patch('PUI.wx.text.OpenURL') as launch:
            for enabled in (False, True, False):
                html.openURL = enabled
                html.ui.OnLinkClicked(wx.html.HtmlLinkInfo('https://example.com'))
                self.assertEqual(launch.call_count, int(enabled))
                launch.reset_mock()

    def test_native_css_selection_retention_and_changed_content(self):
        html = self.mount()
        if not html._webview:
            self.skipTest('Native WebView backend unavailable')
        ui = html.ui
        script = 'document.getElementById("text") ? JSON.stringify([getComputedStyle(document.body).color,getComputedStyle(document.body).backgroundColor,getComputedStyle(document.getElementById("text")).color,getComputedStyle(document.documentElement).webkitUserSelect]) : ""'
        self.wait_script(script, json.dumps(['rgb(18, 52, 86)','rgb(255, 247, 230)','rgb(255, 0, 0)','none'],separators=(',',':')))
        ui.RunScript('window.puiRetained=42')
        self.root.sync()
        self.assertIs(self.root.html.ui,ui)
        self.assertEqual(ui.RunScript('String(window.puiRetained)'),(True,'42'))
        self.root.text = '<b id="changed">Updated</b>'
        self.root.selectable = True
        self.root.sync()
        self.wait_script('document.getElementById("changed")?.textContent || ""','Updated')
        self.assertNotEqual(ui.RunScript('getComputedStyle(document.documentElement).webkitUserSelect')[1],'none')

    def test_fallback_warns_once_and_is_retained(self):
        with patch.object(Html,'_create_webview',side_effect=RuntimeError('missing test runtime')):
            with warnings.catch_warnings(record=True) as seen:
                warnings.simplefilter('always')
                html=self.mount()
                self.root.sync()
            self.assertEqual(len(seen),1)
            self.assertIn('missing test runtime',str(seen[0].message))
            self.assertIn('falling back to HtmlWindow',str(seen[0].message))
            html=self.root.html
            self.assertIsInstance(html.ui,wx.html.HtmlWindow)
            self.assertFalse(html._webview)
            self.assertIn('HTML',html.ui.ToText())
