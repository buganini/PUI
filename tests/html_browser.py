"""Html records and retained updates through both browser runtimes."""
import asyncio
import importlib
import unittest


class BrowserHtmlTests(unittest.IsolatedAsyncioTestCase):
    async def test_html_records_and_updates(self):
        for backend in ('web', 'pyodide'):
            with self.subTest(backend=backend):
                UI = importlib.import_module('PUI.' + backend)
                Runtime = importlib.import_module('PUI.' + backend + '.runtime').Runtime
                options = {} if backend == 'web' else dict(send=lambda message: None, epoch='test', build='test')
                runtime = Runtime(asyncio.get_running_loop(), **options)
                class App(UI.Application):
                    markup = '<b>Hello</b> &amp; <i>world</i>'
                    selectable = True
                    open_url = None
                    def content(self):
                        with UI.Window():
                            UI.Html(self.markup, selectable=self.selectable, **({} if self.open_url is None else {'openURL': self.open_url})).id('html')
                try:
                    self.assertTrue(UI.Html.pui_supported)
                    runtime.app = App()
                    runtime.app.sync()
                    initial = runtime.snapshot()['roots'][0]['children'][0]
                    self.assertEqual(initial['type'], 'Html')
                    self.assertEqual(initial['props'], {'text': runtime.app.markup, 'selectable': True, 'openURL': True})
                    runtime.app.markup = '<p>Updated 中文</p>'
                    runtime.app.selectable = False
                    runtime.app.open_url = False
                    runtime.app.sync()
                    updated = runtime.snapshot()['roots'][0]['children'][0]
                    self.assertEqual(initial['id'], updated['id'])
                    self.assertEqual(updated['props'], {'text': '<p>Updated 中文</p>', 'selectable': False, 'openURL': False})
                finally:
                    runtime.close()


if __name__ == '__main__':
    unittest.main()
