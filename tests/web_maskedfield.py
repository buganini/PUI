"""MaskedField uses the same binding and callback lifecycle as TextField."""
import asyncio
import unittest

from PUI.web import Application, MaskedField, State, Window
from PUI.web.runtime import Runtime


class MaskedFieldTests(unittest.IsolatedAsyncioTestCase):
    async def test_input_commit_retention_and_stale_writes(self):
        for buffered in (False, True):
            with self.subTest(buffered=buffered):
                state = State()
                state.password = ''
                state.draft = ''
                events = []

                class App(Application):
                    placeholder = 'Password'
                    def content(self):
                        with Window():
                            MaskedField(state('password'), state('draft') if buffered else None,
                                        placeholder=self.placeholder).input(
                                lambda e: events.append(('input', e.value))).change(
                                lambda e: events.append(('change', e.value)))

                runtime = Runtime(asyncio.get_running_loop())
                try:
                    runtime.app = App()
                    runtime.app.sync()
                    snapshot = runtime.snapshot()
                    field = snapshot['roots'][0]['children'][0]
                    self.assertEqual(field['type'], 'MaskedField')
                    self.assertEqual(field['props'], {'text': '', 'placeholder': 'Password'})

                    def write(role, phase):
                        a = field['bindings'][role]
                        return {'node_id': field['id'], 'role': role, 'phase': phase,
                            'ref': a['ref'], 'slot_token': a['slot_token'],
                            'attachment_token': a['token'], 'observed_render_rev': 1,
                            'observed_value_rev': 1, 'edit_seq': 1, 'value': 'test-password'}

                    if buffered:
                        result = runtime.action('binding_write', write('edit_model', 'input'))
                    else:
                        result = runtime.action('event', {'node_id': field['id'], 'event': 'input',
                            'token': field['events']['input'], 'observed_render_rev': 1,
                            'data': {'value': 'test-password', 'edit_seq': 1, 'composing': False}})
                    self.assertEqual(result[0], 'processed')
                    self.assertEqual(state.password, '')
                    self.assertEqual(state.draft, 'test-password' if buffered else '')
                    self.assertEqual(events, [('input', 'test-password')])
                    runtime.app.placeholder = 'Updated'
                    runtime.app.redraw()
                    runtime.flush()
                    retained = runtime.snapshot()['roots'][0]['children'][0]
                    self.assertEqual(retained['id'], field['id'])
                    self.assertEqual(retained['bindings'], field['bindings'])
                    commit = write('model', 'commit')
                    self.assertEqual(runtime.action('binding_write', commit)[0], 'processed')
                    self.assertEqual(state.password, 'test-password')
                    self.assertEqual(events[-1], ('change', 'test-password'))
                    self.assertEqual(runtime.action('binding_write', commit)[0], 'stale')
                    runtime.close()
                    self.assertEqual(runtime.action('binding_write', commit)[0], 'stale')
                finally:
                    runtime.close()
