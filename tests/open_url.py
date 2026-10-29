"""Backend URL dispatch, validation and one-shot browser commands."""
import asyncio
import importlib
import unittest
from unittest.mock import patch
from PUI._url import OpenURL, validate_url
from PUI import web
from PUI.web.runtime import Runtime


class URLTests(unittest.TestCase):
    def test_validation(self):
        for url in ('https://example.com/a?q=1#x', 'http://localhost:8000', 'mailto:me@example.com'):
            self.assertEqual(validate_url(url), url)
        for url in ('', '/relative', 'javascript:alert(1)', 'data:text/html,x', 'https://', 'mailto:', ' https://example.com', 'https://example.com\n'):
            with self.subTest(url=url), self.assertRaises(ValueError): validate_url(url)
        with self.assertRaises(TypeError): validate_url(None)

    def test_desktop_exports(self):
        for backend in ('PySide6', 'wx', 'tkinter', 'textual', 'flet'):
            self.assertIs(importlib.import_module('PUI.'+backend).OpenURL, OpenURL)
        with patch('webbrowser.open_new_tab', return_value=True) as launch:
            self.assertIsNone(OpenURL('https://example.com'))
            launch.assert_called_once_with('https://example.com')
        with patch('webbrowser.open_new_tab', return_value=False), self.assertRaises(RuntimeError):
            OpenURL('https://example.com')


class BrowserURLTests(unittest.IsolatedAsyncioTestCase):
    async def test_click_command_and_cleanup(self):
        class App(web.Application):
            def content(self):
                with web.Window():
                    web.Button('Website').click(lambda e: web.OpenURL('https://example.com'))
        runtime=Runtime(asyncio.get_running_loop())
        try:
            runtime.app=App();runtime.app.sync();runtime.flush();runtime.snapshot()
            button=runtime.app.children[0].children[0]
            body=dict(node_id=button.ui.id,event='click',token=button.ui.events['click'],observed_render_rev=1,data={})
            with patch('webbrowser.open_new_tab') as launch:
                self.assertEqual(runtime.action('event',body)[0], 'processed')
                launch.assert_not_called()
            self.assertEqual(runtime.take_open_urls(), ['https://example.com'])
            self.assertEqual(runtime.take_open_urls(), [])
            web.OpenURL('https://example.com');runtime.reset_connection()
            self.assertEqual(runtime.take_open_urls(), [])
            web.OpenURL('https://example.com');runtime.close()
            self.assertEqual(runtime.take_open_urls(), [])
            with self.assertRaises(RuntimeError): web.OpenURL('https://example.com')
        finally: runtime.close()

    async def test_pyodide_delivery(self):
        from PUI import pyodide
        from PUI.pyodide.runtime import Runtime as PyodideRuntime
        messages=[]
        class App(pyodide.Application):
            def content(self):
                with pyodide.Window(): pyodide.Label('URL test')
        runtime=PyodideRuntime(asyncio.get_running_loop(),messages.append,epoch='test',build='test')
        try:
            runtime.start(App())
            pyodide.OpenURL('https://example.com')
            for _ in range(10): await asyncio.sleep(0)
            self.assertEqual([m['body'] for m in messages if m['type']=='open_url'],[{'url':'https://example.com'}])
        finally:
            runtime.close()
            if runtime.task:
                runtime.task.cancel()
                await asyncio.gather(runtime.task,return_exceptions=True)

if __name__=='__main__': unittest.main()
