"""Application(icon=...) and Window(icon=...) are accepted by every backend.

    PYTHONPATH=. env/bin/python tests/application_icon.py

Each backend runs in a child process (toolkits keep global state). Backends
that are not installed are skipped. Where the toolkit shows icons, the test
also checks that the icon was applied; elsewhere the option must not crash.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNG = str(ROOT / 'PUI' / 'cookbook' / 'assets' / 'star.png')

CHILD = r'''
import asyncio, importlib, os, sys
backend, icon = sys.argv[1], sys.argv[2]
UI = importlib.import_module('PUI.' + backend)

class App(UI.Application):
    def content(self):
        with UI.Window(title='Icon', icon=icon):
            UI.Label('icon')

if backend == 'PySide6':
    app = App(icon=icon)
    app.redraw()
    window = next(c for c in app.children if isinstance(c, UI.Window)).ui
    assert not app.ui.windowIcon().isNull(), 'application icon not set'
    assert not window.windowIcon().isNull(), 'window icon not set'
elif backend == 'wx':
    app = App(icon=icon)
    app.redraw()
elif backend == 'tkinter':
    app = App(icon=icon)
    app.redraw()
    if icon.endswith('star.png'):
        assert app._icon_photo is not None, 'application icon not loaded'
    app.ui.destroy()
elif backend == 'textual':
    async def run():
        app = App(icon=icon)
        async with app.ui.run_test(size=(40, 10)) as pilot:
            await pilot.pause()
    asyncio.run(run())
elif backend == 'lvgl':
    app = App(icon=icon)
    app.redraw()
    app.process_events()
    app.quit()
elif backend == 'web':
    from PUI.web.runtime import Runtime
    async def run():
        runtime = Runtime(asyncio.get_running_loop())
        runtime.app = App(icon=icon)
        runtime.app.sync()
        runtime.flush()
        state = runtime.snapshot()
        def windows(node):
            if node['type'] == 'Window':
                yield node
            for child in node['children']:
                yield from windows(child)
        found = [w for root in state['roots'] for w in windows(root)]
        assert found and found[0]['props'].get('icon'), 'favicon not published'
        runtime.close()
    asyncio.run(run())
elif backend == 'pyodide':
    # Browser widgets need the worker runtime; Web covers the shared renderer.
    import inspect
    App(icon=icon)
    assert 'icon' in inspect.signature(UI.Window).parameters
else:  # flet: declarations only (its runtime needs a client)
    App(icon=icon)
    UI.Window(title='Icon', icon=icon)
print('ok', flush=True)
'''


def available(backend):
    module = {'PySide6': 'PySide6', 'wx': 'wx', 'tkinter': 'tkinter', 'flet': 'flet',
              'textual': 'textual', 'web': 'aiohttp', 'pyodide': None, 'lvgl': None}[backend]
    if backend == 'lvgl':
        return any(p.name.startswith('liblvgl_') for p in (ROOT / 'PUI' / 'lvgl').iterdir())
    return module is None or importlib.util.find_spec(module) is not None


class ApplicationIcon(unittest.TestCase):
    def run_backend(self, backend, icon=PNG):
        if not available(backend):
            self.skipTest(backend + ' is not installed')
        env = dict(os.environ, PYTHONPATH=str(ROOT), QT_QPA_PLATFORM='offscreen',
                   PUI_LVGL_DRIVER='headless#width=320#height=240')
        env.pop('PUI_LVGL_LIB', None)
        result = subprocess.run([sys.executable, '-c', CHILD, backend, icon], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-3000:])
        self.assertIn('ok', result.stdout)
        return result

    def test_pyside6(self):
        self.run_backend('PySide6')

    def test_wx(self):
        self.run_backend('wx')

    def test_tkinter(self):
        self.run_backend('tkinter')

    def test_tkinter_unreadable_icon_only_warns(self):
        with tempfile.TemporaryDirectory() as directory:
            broken = os.path.join(directory, 'icon.png')
            Path(broken).write_bytes(b'not an image')
            result = self.run_backend('tkinter', broken)
        self.assertIn('cannot load icon', result.stderr)

    def test_flet(self):
        self.run_backend('flet')

    def test_textual(self):
        self.run_backend('textual')

    def test_web(self):
        self.run_backend('web')

    def test_pyodide(self):
        self.run_backend('pyodide')

    def test_lvgl(self):
        self.run_backend('lvgl')


if __name__ == '__main__':
    unittest.main()
