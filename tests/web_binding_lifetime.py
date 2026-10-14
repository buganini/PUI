import asyncio
import unittest
from PUI.web import Application, Window, TextField, State
from PUI.web.runtime import Runtime


class App(Application):
    def setup(self):
        self.items = State(['first', 'second'])
        self.mapping = State({'keep': 'old', 1: 'integer', '1': 'string'})
        self.inputs = []

    def content(self):
        with Window():
            for index in range(len(self.items)):
                TextField(self.items(index)).id('index' + str(index)).input(lambda e: self.inputs.append(e.value))
            for key in self.mapping:
                TextField(self.mapping(key)).id(type(key).__name__ + str(key))


class LifetimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = App()
        self.runtime.app.sync()
        self.runtime.snapshot()

    async def asyncTearDown(self):
        self.runtime.close()

    def write(self, name, value='updated'):
        editor = next(e for e in self.runtime.nodes.values() if e.node._id == name)
        a = editor.attachments['model']
        return {'node_id': editor.id, 'role': 'model', 'phase': 'commit', 'ref': a['ref'],
            'slot_token': a['slot_token'], 'attachment_token': a['token'],
            'observed_render_rev': 1, 'observed_value_rev': 1, 'edit_seq': 1, 'value': value}

    def refresh(self):
        self.runtime.flush()
        self.runtime.snapshot()

    def test_list_shift_rejects_old_action_even_before_redraw(self):
        old = self.write('index0')
        self.runtime.app.items.insert(0, 'inserted')
        self.assertEqual(self.runtime.action('binding_write', old)[0], 'stale')
        self.assertEqual(self.runtime.app.items[0], 'inserted')
        self.refresh()
        new = self.write('index0')
        self.assertNotEqual(old['slot_token'], new['slot_token'])
        self.assertNotEqual(old['attachment_token'], new['attachment_token'])
        self.assertEqual(self.runtime.action('binding_write', old)[0], 'stale')
        self.assertEqual(self.runtime.action('binding_write', new)[0], 'processed')
        self.assertEqual(self.runtime.app.items[0], 'updated')

    def test_dictionary_recreation_only_revokes_affected_key(self):
        keep, old = self.write('strkeep'), self.write('int1')
        with self.runtime.app.mapping:
            del self.runtime.app.mapping[1]
            self.runtime.app.mapping[1] = 'replacement'
        self.assertEqual(self.runtime.action('binding_write', old)[0], 'stale')
        self.refresh()
        self.assertEqual(self.write('strkeep'), keep)
        self.assertNotEqual(self.write('int1')['slot_token'], old['slot_token'])
        self.assertEqual(self.runtime.action('binding_write', keep)[0], 'processed')
        self.assertEqual(self.runtime.action('binding_write', self.write('str1', 'text key'))[0], 'processed')
        self.assertEqual(self.runtime.app.mapping[1], 'replacement')
        self.assertEqual(self.runtime.app.mapping['1'], 'text key')

    def test_list_value_write_keeps_current_registration(self):
        body = self.write('index0')
        self.assertEqual(self.runtime.action('binding_write', body)[0], 'processed')
        self.refresh()
        self.assertEqual(self.write('index0'), body)
        self.assertEqual(self.runtime.action('binding_write', dict(body, edit_seq=2, value='again'))[0], 'processed')
        self.assertEqual(len(self.runtime.slots), 5)

    def test_structural_change_also_revokes_input_callback(self):
        editor = next(e for e in self.runtime.nodes.values() if e.node._id == 'index0')
        event = {'node_id': editor.id, 'event': 'input', 'token': editor.events['input'],
                 'observed_render_rev': 1, 'data': {'value': 'stale draft', 'edit_seq': 1, 'composing': False}}
        self.runtime.app.items.reverse()
        self.assertEqual(self.runtime.action('event', event)[0], 'stale')
        self.refresh()
        self.assertNotEqual(editor.events['input'], event['token'])
        self.assertEqual(self.runtime.action('event', event)[0], 'stale')
        self.assertEqual(self.runtime.app.inputs, [])
