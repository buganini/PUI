"""Retained binding registrations, independent subviews and timer teardown."""
import asyncio
from copy import deepcopy
import unittest
from PUI.web import Application, PUIView, Window, Label, TextField, State, TimelineView
from PUI.web.runtime import Runtime


class Editor(PUIView):
    def content(self):
        app = self.args[0]
        shared, counts, timer = app.shared, app.counts, app.timer
        counts['child'] += 1
        TextField(shared('text')).id('first').input(lambda event: counts['inputs'].append(event.value))
        TextField(shared('text')).id('second')
        if timer:
            with TimelineView(.02):
                Label('tick')


class App(Application):
    def setup(self):
        self.shared = State()
        self.shared.text = 'one'
        self.counts = {'parent': 0, 'child': 0, 'inputs': []}
        self.visible, self.timer = True, False

    def content(self):
        self.counts['parent'] += 1
        with Window('Lifecycle'):
            Label('outside')
            if self.visible:
                Editor(self)


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = App()
        self.runtime.app.sync()
        self.runtime.snapshot()

    async def asyncTearDown(self):
        self.runtime.close()

    def editors(self):
        return [e for e in self.runtime.nodes.values() if e.node.wire_type == 'TextField']

    def redraw(self):
        self.runtime.app.redraw()
        self.runtime.flush()
        return self.runtime.snapshot()

    def write(self, editor, value='updated'):
        a = editor.attachments['model']
        return {'node_id': editor.id, 'role': 'model', 'phase': 'commit', 'ref': a['ref'],
            'slot_token': a['slot_token'], 'attachment_token': a['token'],
            'observed_render_rev': 1, 'observed_value_rev': 1, 'edit_seq': 1, 'value': value}

    def test_independent_subview_redraw_retains_shared_slot_and_event(self):
        first, second = self.editors()
        attachment = deepcopy(first.attachments['model'])
        token = first.events['input']
        parents = self.runtime.app.counts['parent']
        self.assertEqual(len(self.runtime.slots), 1)
        self.assertEqual(attachment['slot_token'], second.attachments['model']['slot_token'])
        self.assertNotEqual(attachment['token'], second.attachments['model']['token'])
        self.runtime.app.shared.text = 'two'
        self.runtime.flush()
        self.runtime.snapshot()
        self.assertEqual(self.runtime.app.counts['parent'], parents)
        self.assertGreater(self.runtime.app.counts['child'], 1)
        self.assertIs(self.editors()[0], first)
        self.assertEqual(first.attachments['model'], attachment)
        self.assertEqual(first.events['input'], token)
        body = {'node_id': first.id, 'event': 'input', 'token': token,
            'observed_render_rev': 1, 'data': {'value': 'draft', 'edit_seq': 1, 'composing': False}}
        self.assertEqual(self.runtime.action('event', body)[0], 'processed')
        self.assertEqual(self.runtime.app.counts['inputs'], ['draft'])

    def test_removed_and_readded_source_has_new_registration(self):
        old = self.write(self.editors()[0])
        self.runtime.app.visible = False
        self.redraw()
        self.assertEqual(self.runtime.slots, {})
        self.assertEqual(self.runtime.edits, {})
        self.assertEqual(self.runtime.action('binding_write', old)[0], 'stale')
        self.runtime.app.visible = True
        self.redraw()
        new = self.write(self.editors()[0])
        self.assertEqual(new['ref'], old['ref'])  # exact same Python object ID
        self.assertNotEqual(new['slot_token'], old['slot_token'])
        self.assertNotEqual(new['attachment_token'], old['attachment_token'])
        self.assertEqual(self.runtime.action('binding_write', old)[0], 'stale')
        self.assertEqual(self.runtime.action('binding_write', new)[0], 'processed')

    def test_rebinding_retained_editor_rejects_previous_source(self):
        first = self.editors()[0]
        old = self.write(first)
        previous = self.runtime.app.shared
        self.runtime.app.shared = State()
        self.runtime.app.shared.text = 'replacement'
        first.node.root.redraw()
        self.runtime.flush()
        self.runtime.snapshot()
        self.assertIs(self.editors()[0], first)
        self.assertNotEqual(first.attachments['model']['ref'], old['ref'])
        self.assertEqual(self.runtime.action('binding_write', old)[0], 'stale')
        self.assertEqual(previous.text, 'one')
        self.assertEqual(self.runtime.app.shared.text, 'replacement')
        self.assertEqual(len(self.runtime.slots), 1)

    def test_custom_binding_reads_back_normalized_values(self):
        class Uppercase:
            def __init__(self):
                self._value = 'START'
            @property
            def value(self):
                return self._value
            @value.setter
            def value(self, value):
                self._value = value.upper()
        custom = Uppercase()
        editor = self.editors()[0]
        editor.node.model = custom
        self.runtime.snapshot()
        body = self.write(editor, 'normalized')
        self.assertEqual(body['ref'], {'object_id': str(id(custom)), 'kind': 'value', 'key': None})
        self.assertEqual(self.runtime.action('binding_write', body)[0], 'processed')
        snapshot = self.runtime.snapshot()
        slot = next(slot for slot in snapshot['bindings'] if slot['token'] == body['slot_token'])
        self.assertEqual(slot['value'], 'NORMALIZED')
        self.assertEqual(slot['value_rev'], 2)

    async def test_timer_redraw_is_queued_and_removed_timer_stops(self):
        self.runtime.app.timer = True
        self.editors()[0].node.root.redraw()
        self.runtime.flush()
        self.runtime.snapshot()
        await asyncio.sleep(0)  # finish previously queued wake notifications
        self.runtime.changed.clear()
        builds = self.runtime.app.counts['child']
        await asyncio.wait_for(self.runtime.changed.wait(), 1)
        self.assertEqual(self.runtime.app.counts['child'], builds)
        self.runtime.flush()
        self.runtime.snapshot()
        self.assertGreater(self.runtime.app.counts['child'], builds)
        self.runtime.app.visible = False
        self.redraw()
        builds = self.runtime.app.counts['child']
        await asyncio.sleep(.06)
        self.runtime.flush()
        self.assertEqual(self.runtime.app.counts['child'], builds)

    def test_close_releases_queued_views_and_edit_sequences(self):
        self.runtime.action('binding_write', self.write(self.editors()[0]))
        self.assertTrue(self.runtime._dirty)
        self.assertTrue(self.runtime.edits)
        queued = next(iter(self.runtime._dirty))
        self.runtime.close()
        self.runtime.queue_view(queued)  # a late timer callback cannot retain it
        self.assertFalse(self.runtime._dirty)
        self.assertFalse(self.runtime.edits)
        self.assertFalse(self.runtime.nodes)
        self.assertFalse(self.runtime.slots)
