"""Invalid messages must not reach callbacks or consume editor sequence numbers."""
import asyncio
from copy import deepcopy
import unittest

from PUI.web.messages import validate_client_body
from PUI.web.protocol import ProtocolError
from PUI.web.runtime import Runtime
from web_fixture import App


class MessageTests(unittest.TestCase):
    def test_hello_validates_nested_viewport_and_capabilities(self):
        body = {'client_build': 'test', 'capabilities': ['render.snapshot'],
                'viewport': {'width': 0, 'height': 700, 'dpr': 1.5}, 'resume_id': None}
        validate_client_body('hello', body)
        for change in ({'viewport': []}, {'viewport': {'width': True, 'height': 1, 'dpr': 1}},
                       {'viewport': {'width': 1, 'height': 1, 'dpr': 0}},
                       {'capabilities': ['x', 'x']}, {'capabilities': [{}]}, {'resume_id': 1}):
            with self.subTest(change=change), self.assertRaises(ProtocolError):
                validate_client_body('hello', dict(body, **change))

    def test_control_schema_does_not_treat_boolean_as_revision(self):
        for kind, body in (
            ('ack', {'render_rev': True, 'applied_rev': 1, 'status': 'applied'}),
            ('ack', {'render_rev': 1, 'applied_rev': 0, 'status': 'applied'}),
            ('ack', {'render_rev': 1, 'applied_rev': 0, 'status': []}),
            ('resync', {'last_applied_rev': False}), ('close', {'reason': []}),
            ('close', {}), ('measure', {}), ('ready', {}),
        ):
            with self.subTest(kind=kind, body=body), self.assertRaises(ProtocolError):
                validate_client_body(kind, body)


class ActionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = App()
        self.runtime.app.sync()
        self.runtime.snapshot()
        self.button = next(e for e in self.runtime.nodes.values() if e.node.wire_type == 'Button')
        self.editor = next(e for e in self.runtime.nodes.values() if e.node.wire_type == 'TextField')
        self.click = {'node_id': self.button.id, 'event': 'click',
                      'token': self.button.events['click'], 'observed_render_rev': 1, 'data': {}}
        attachment = self.editor.attachments['model']
        self.write = {'node_id': self.editor.id, 'role': 'model', 'phase': 'commit',
            'ref': attachment['ref'], 'slot_token': attachment['slot_token'],
            'attachment_token': attachment['token'], 'observed_render_rev': 1,
            'observed_value_rev': 1, 'edit_seq': 1, 'value': '2.5'}

    async def asyncTearDown(self):
        self.runtime.close()

    def test_invalid_events_cannot_run_callback(self):
        for change in ({'node_id': []}, {'event': {}}, {'token': []}, {'data': []},
                       {'observed_render_rev': True}, {'observed_render_rev': 2}, {'extra': 1}):
            with self.subTest(change=change):
                self.assertEqual(self.runtime.action('event', dict(self.click, **change), render_rev=1)[0], 'invalid')
                self.assertEqual(self.runtime.app.state.count, 0)
        self.assertEqual(self.runtime.action('event', self.click, render_rev=1), ('processed', None))
        self.assertEqual(self.runtime.app.state.count, 1)

    def test_invalid_edits_do_not_write_or_consume_edit_sequence(self):
        for change in ({'ref': []}, {'ref': {'object_id': '1', 'kind': 'attr', 'key': []}},
                       {'observed_value_rev': 2}, {'observed_value_rev': True}, {'role': []},
                       {'phase': {}}, {'value': {}}, {'edit_seq': False}):
            with self.subTest(change=change):
                self.assertEqual(self.runtime.action('binding_write', dict(self.write, **change), render_rev=1)[0], 'invalid')
                self.assertEqual(self.runtime.app.state.text, 1.23)
        self.assertEqual(self.runtime.action('binding_write', self.write, render_rev=1), ('processed', None))
        self.assertEqual(self.runtime.app.state.text, 2.5)
        self.assertEqual(self.runtime.action('binding_write', self.write, render_rev=1)[0], 'stale')

    def test_queued_old_value_revision_still_applies_to_live_attachment(self):
        self.runtime.action('binding_write', self.write, render_rev=1)
        self.runtime.flush()
        self.runtime.snapshot()
        later = dict(self.write, edit_seq=2, value='3.5')
        self.assertEqual(self.runtime.action('binding_write', later, render_rev=2), ('processed', None))
        self.assertEqual(self.runtime.app.state.text, 3.5)

    def test_input_callback_is_deduplicated_per_registration(self):
        calls = []
        self.editor.node.input(lambda event: calls.append(event.value))
        self.runtime.snapshot()
        event = {'node_id': self.editor.id, 'event': 'input', 'token': self.editor.events['input'],
                 'observed_render_rev': 1, 'data': {'value': 'draft', 'edit_seq': 1, 'composing': False}}
        self.assertEqual(self.runtime.action('event', event, render_rev=1)[0], 'processed')
        self.runtime.snapshot()
        self.assertEqual(self.runtime.action('event', deepcopy(event), render_rev=1)[0], 'stale')
        self.assertEqual(calls, ['draft'])
        self.assertEqual(self.runtime.app.state.text, 1.23)
