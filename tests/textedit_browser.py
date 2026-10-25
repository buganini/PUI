"""Shared Web/Pyodide multiline bindings and readonly enforcement."""
import asyncio
import importlib
import inspect
import unittest

from PUI import State


class BrowserTextEditTests(unittest.IsolatedAsyncioTestCase):
    async def test_both_runtimes(self):
        for backend in ('web', 'pyodide'):
            for buffered in (False, True):
                with self.subTest(backend=backend, buffered=buffered):
                    UI = importlib.import_module('PUI.' + backend)
                    Runtime = importlib.import_module('PUI.' + backend + '.runtime').Runtime
                    options = {} if backend == 'web' else dict(send=lambda message: None, epoch='test', build='test')
                    runtime = Runtime(asyncio.get_running_loop(), **options)
                    state, events = State(), []
                    state.text, state.draft = '', ''
                    class App(UI.Application):
                        readonly = False
                        def content(self):
                            with UI.Window():
                                UI.TextEdit(state('text'), state('draft') if buffered else None,
                                            readonly=self.readonly, wrap=False, placeholder='Hint').input(
                                    lambda e: events.append(('input', e.value))).change(
                                    lambda e: events.append(('change', e.value)))
                    try:
                        runtime.app = App()
                        runtime.app.sync()
                        field = runtime.snapshot()['roots'][0]['children'][0]
                        self.assertEqual(field['type'], 'TextEdit')
                        self.assertEqual(field['props'], {'text': '', 'placeholder': 'Hint', 'readonly': False, 'wrap': False})
                        def write(role, phase, seq=1):
                            a = field['bindings'][role]
                            return {'node_id': field['id'], 'role': role, 'phase': phase,
                                'ref': a['ref'], 'slot_token': a['slot_token'], 'attachment_token': a['token'],
                                'observed_render_rev': 1, 'observed_value_rev': 1, 'edit_seq': seq, 'value': 'a\n中文'}
                        event = {'node_id': field['id'], 'event': 'input', 'token': field['events']['input'],
                                 'observed_render_rev': 1, 'data': {'value': 'a\n中文', 'edit_seq': 1, 'composing': False}}
                        result = runtime.action('binding_write', write('edit_model', 'input')) if buffered else runtime.action('event', event)
                        self.assertEqual(result[0], 'processed')
                        self.assertEqual(state.text, '')
                        self.assertEqual(state.draft, 'a\n中文' if buffered else '')
                        self.assertEqual(runtime.action('binding_write', write('model', 'commit'))[0], 'processed')
                        self.assertEqual(state.text, 'a\n中文')
                        self.assertEqual(events, [('input', 'a\n中文'), ('change', 'a\n中文')])
                        runtime.app.readonly = True
                        runtime.app.sync()
                        field = runtime.snapshot()['roots'][0]['children'][0]
                        self.assertEqual(runtime.action('binding_write', write('model', 'commit', 2))[0], 'stale')
                        event['token'] = field['events']['input']
                        event['data']['edit_seq'] = 2
                        self.assertEqual(runtime.action('event', event)[0], 'stale')
                    finally:
                        runtime.close()

    async def test_common_signature(self):
        for backend in ('PySide6', 'wx', 'tkinter', 'textual', 'flet', 'web', 'pyodide'):
            cls = importlib.import_module('PUI.' + backend).TextEdit
            args = inspect.signature(cls).parameters
            self.assertEqual(list(args), ['model', 'edit_model', 'placeholder', 'readonly', 'wrap'])
            for name, default in [('edit_model', None), ('placeholder', None), ('readonly', False), ('wrap', True)]:
                self.assertIs(args[name].default, default)
            self.assertEqual(args['placeholder'].kind, inspect.Parameter.KEYWORD_ONLY)
