"""Menu records and callbacks shared by Web and Pyodide."""
import asyncio
import importlib
import unittest


class BrowserMenuTests(unittest.IsolatedAsyncioTestCase):
    async def test_menus_and_retained_callbacks(self):
        for backend in ('web', 'pyodide'):
            with self.subTest(backend=backend):
                ui = importlib.import_module('PUI.' + backend)
                runtime_class = importlib.import_module('PUI.' + backend + '.runtime').Runtime
                options = {} if backend == 'web' else dict(send=lambda message: None, epoch='test', build='test')
                runtime = runtime_class(asyncio.get_running_loop(), **options)
                calls = []
                class App(ui.Application):
                    names = ['One', 'Two']
                    generation = 0
                    shown = True
                    def content(self):
                        with ui.Window():
                            if self.shown:
                                with ui.MenuBar(native=False):
                                    with ui.Menu('File'):
                                        for name in self.names:
                                            ui.MenuAction(name, native=False).id(name).trigger(calls.append, (name, self.generation))
                                        with ui.Menu('Nested'):
                                            ui.MenuAction('Deep').trigger(calls.append, 'deep')
                            ui.Label('Content')
                try:
                    runtime.app = App()
                    runtime.app.sync()
                    tree = runtime.snapshot()['roots'][0]
                    self.assertEqual([n['type'] for n in tree['children']], ['MenuBar', 'Label'])
                    action = tree['children'][0]['children'][0]['children'][0]
                    body = dict(node_id=action['id'], event='click', token=action['events']['click'], observed_render_rev=1, data={})
                    self.assertEqual(runtime.action('event', body, render_rev=1)[0], 'processed')
                    self.assertEqual(calls, [('One', 0)])
                    runtime.app.generation = 1
                    runtime.app.names.reverse()
                    runtime.app.sync()
                    menu = runtime.snapshot()['roots'][0]['children'][0]['children'][0]
                    self.assertEqual(menu['children'][1]['id'], action['id'])
                    body.update(token=menu['children'][1]['events']['click'], observed_render_rev=2)
                    self.assertEqual(runtime.action('event', body, render_rev=2)[0], 'processed')
                    self.assertEqual(calls[-1], ('One', 1))
                    runtime.app.shown = False
                    runtime.app.sync()
                    runtime.snapshot()
                    self.assertEqual(runtime.action('event', body, render_rev=3)[0], 'stale')
                finally:
                    runtime.close()
