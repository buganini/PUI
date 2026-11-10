import asyncio
import unittest
from PUI import State
from PUI.web import Application, Window, FontComboBox
from PUI.web.runtime import Runtime


class BrowserFontTests(unittest.IsolatedAsyncioTestCase):
    async def test_selection_retention_disabled_and_defaults(self):
        class App(Application):
            fonts = ('Alpha', 'Beta')
            disabled = False
            def setup(self): self.state = State({'font': 'Alpha'})
            def content(self):
                with Window():
                    self.picker = FontComboBox(self.state('font'), fonts=self.fonts, disabled=self.disabled)
        runtime = Runtime(asyncio.get_running_loop())
        runtime.app = App()
        def sync():
            runtime.app.sync(); runtime.flush(); runtime.snapshot()
        try:
            sync()
            app = runtime.app
            picker = app.picker
            original = picker.ui.id
            event = dict(node_id=original, event='choose', token=picker.ui.events['choose'],
                         observed_render_rev=1, data={'item_id': picker.children[1].ui.id})
            self.assertEqual(runtime.action('event', event)[0], 'processed')
            self.assertEqual(app.state['font'], 'Beta')
            app.disabled = True
            sync()
            self.assertEqual(app.picker.ui.id, original)
            self.assertTrue(app.picker.properties()['disabled'])
            app.fonts = None
            sync()
            self.assertEqual([c.value for c in app.picker.children], ['sans-serif', 'serif', 'monospace'])
            self.assertEqual(app.state['font'], 'Beta')
            from PUI.pyodide import FontComboBox as PyFont
            self.assertIs(PyFont, FontComboBox)
        finally:
            runtime.close()
