"""Native controls preserve Python values and reject obsolete selections/edits."""
import asyncio
import unittest

from PUI.web import (Application, Window, State, Checkbox, RadioButton,
                     ComboBox, ComboBoxItem)
from PUI.state import Unstate, DummyBinding
from PUI.web.runtime import Runtime


class App(Application):
    def setup(self):
        self.state = State()
        self.state.flag = False
        self.state.items = []
        self.state.mapping = {}
        self.state.radio = None
        self.state.index = -1
        self.state.value = None
        self.choices = [('same', 7), ('same', False), ('third', 'raw')]
        self.autoexpand = True
        self.editable = False
        self.disabled = False
        self.calls = []
        self.free = DummyBinding('')
        self.draft = DummyBinding('')

    def content(self):
        with Window():
            Checkbox('flag', self.state('flag'), disabled=self.disabled).id('flag').click(
                lambda e: self.calls.append(('flag', e.value, self.state.flag)))
            Checkbox('list', self.state('items'), 7).id('list')
            Checkbox('dict', self.state('mapping'), 'key').id('dict')
            RadioButton('integer', 7, self.state('radio'), disabled=self.disabled).id('radio').click(
                lambda e: self.calls.append(('radio', e.value, self.state.radio)))
            with ComboBox(self.editable, index_model=self.state('index'), text_model=self.state('value'),
                          disabled=self.disabled, autoexpand=self.autoexpand).id('combo').change(lambda e: self.calls.append(('combo', e.value))):
                for index, (text, value) in enumerate(self.choices):
                    ComboBoxItem(text, value).id(index)
            with ComboBox(editable=True, text_model=self.free, edit_model=self.draft).id('free').input(
                    lambda e: self.calls.append(('input', e.value))):
                ComboBoxItem('display', 'raw')
            with ComboBox().id('unbound'):
                for text in ('one', 'two'):
                    ComboBoxItem(text)


class ControlsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = App()
        self.refresh()

    async def asyncTearDown(self):
        self.runtime.close()

    def test_combo_input_notifies_without_committing_and_survives_choice_changes(self):
        node = self.node('free')
        token = node.ui.events['input']
        body = {'node_id': node.ui.id, 'event': 'input', 'token': token,
                'observed_render_rev': 0,
                'data': {'value': 'query', 'edit_seq': 1, 'composing': False}}
        self.assertEqual(self.runtime.action('event', body)[0], 'processed')
        self.assertEqual(self.runtime.app.calls[-1], ('input', 'query'))
        self.assertEqual(self.runtime.app.free.value, '')
        node.children[0].text = 'Unrelated candidate'
        self.runtime.snapshot()
        self.assertEqual(node.ui.events['input'], token)
        self.assertEqual(self.runtime.action('event', body)[0], 'stale')
        self.runtime.app.free = DummyBinding('')
        self.refresh()
        self.assertNotEqual(self.node('free').ui.events['input'], token)
        self.assertEqual(self.runtime.action('event', body)[0], 'stale')

    def test_combo_edit_model_write_retains_generation_and_rejects_replay(self):
        node = self.node('free')
        attachment = node.ui.attachments['edit_model']
        body = dict(node_id=node.ui.id, role='edit_model', phase='input',
                    attachment_token=attachment['token'], slot_token=attachment['slot_token'],
                    ref=attachment['ref'], observed_value_rev=1,
                    edit_seq=1, value='draft', observed_render_rev=0)
        self.assertEqual(self.runtime.action('binding_write', body)[0], 'processed')
        self.assertEqual(self.runtime.app.draft.value, 'draft')
        self.assertEqual(self.runtime.app.free.value, '')
        self.assertEqual(self.runtime.app.calls[-1], ('input', 'draft'))
        self.refresh()
        self.assertEqual(self.runtime.action('binding_write', body)[0], 'stale')
        self.runtime.app.draft = DummyBinding('')
        self.refresh()
        body['edit_seq'] = 2
        self.assertEqual(self.runtime.action('binding_write', body)[0], 'stale')

    def test_autocomplete_wire_flag_and_retained_control(self):
        node = self.node('combo')
        element = node.ui
        for enabled in (True, False, True):
            self.runtime.app.autoexpand = enabled
            self.refresh()
            node = self.node('combo')
            self.assertIs(node.ui, element)
            self.assertEqual(node.properties()['autoexpand'], enabled)

    def refresh(self):
        self.runtime.app.sync()
        self.runtime.flush()
        return self.runtime.snapshot()

    def node(self, key):
        return next(e.node for e in self.runtime.nodes.values() if e.node._id == key)

    def event(self, key, data):
        node = self.node(key)
        return {'node_id': node.ui.id, 'event': node.native_event, 'token': node.ui.events[node.native_event],
                'observed_render_rev': 1, 'data': data}

    def apply(self, key, data):
        self.assertEqual(self.runtime.action('event', self.event(key, data)), ('processed', None))
        self.runtime.flush()
        self.runtime.snapshot()

    def test_checkbox_collections_and_radio_callback_observe_updated_values(self):
        self.apply('flag', {'checked': True})
        self.apply('list', {'checked': True})
        self.apply('dict', {'checked': True})
        self.apply('radio', {})
        state = self.runtime.app.state
        self.assertEqual(Unstate(state.items), [7])
        self.assertEqual(Unstate(state.mapping), {'key': True})
        self.assertIs(type(state.radio), int)
        self.assertEqual(self.runtime.app.calls, [('flag', True, True), ('radio', 7, 7)])
        self.apply('list', {'checked': False})
        self.apply('dict', {'checked': False})
        self.assertEqual(Unstate(state.items), [])
        self.assertEqual(Unstate(state.mapping), {})

    def test_readonly_typed_choices_and_unbound_selection(self):
        for index, expected in enumerate((7, False, 'raw')):
            self.runtime.app.state.value = None
            self.refresh()
            self.apply('combo', {'item_id': self.node('combo').children[index].ui.id})
            state = self.runtime.app.state
            self.assertEqual(state.index, index)
            self.assertEqual(state.value, expected)
            self.assertIs(type(state.value), type(expected))
        self.apply('unbound', {'item_id': self.node('unbound').children[1].ui.id})
        self.refresh()
        self.assertEqual(self.node('unbound').properties()['text'], 'two')

    def test_disabled_selection_blocks_events_and_preserves_model_updates(self):
        events = [self.event('flag', {'checked': False}), self.event('radio', {})]
        native = [self.node(key).ui for key in ('flag', 'radio')]
        for disabled in (True, False, True):
            self.runtime.app.disabled = disabled
            self.runtime.app.state.flag = True
            self.runtime.app.state.radio = 7
            self.refresh()
            for key, ui in zip(('flag', 'radio'), native):
                node = self.node(key)
                self.assertIs(node.ui, ui)
                self.assertEqual(node.properties()['disabled'], disabled)
                self.assertTrue(node.properties()['checked'])
            if disabled:
                for event in events:
                    self.assertEqual(self.runtime.action('event', event), ('stale', 'STALE_TARGET'))
                self.assertTrue(self.runtime.app.state.flag)
                self.assertEqual(self.runtime.app.state.radio, 7)
                self.assertEqual(self.runtime.app.calls, [])
        self.runtime.app.disabled = False
        self.refresh()
        self.apply('flag', {'checked': False})
        self.assertFalse(self.runtime.app.state.flag)

    def test_editable_first_label_match_free_text_and_commit_deduplication(self):
        self.runtime.app.editable = True
        self.refresh()
        event = self.event('combo', {'value': 'same', 'edit_seq': 1, 'composing': False})
        self.assertEqual(self.runtime.action('event', event)[0], 'processed')
        self.refresh()
        self.assertEqual(self.runtime.action('event', event)[0], 'stale')
        self.assertEqual(self.runtime.app.state.index, 0)
        self.assertEqual(self.runtime.app.state.value, 7)
        self.apply('combo', {'value': 'free', 'edit_seq': 2, 'composing': False})
        self.assertEqual(self.runtime.app.state.index, -1)
        # Existing AttrBinding conversion follows the model's declared type.
        self.assertEqual(self.runtime.app.state.value, 7)  # integer rejects nonnumeric free text
        self.apply('free', {'value': 'display', 'edit_seq': 1, 'composing': False})
        self.assertEqual(self.runtime.app.free.value, 'raw')
        self.apply('free', {'value': 'custom text', 'edit_seq': 2, 'composing': False})
        self.assertEqual(self.runtime.app.free.value, 'custom text')
        self.assertEqual(self.node('free').properties()['text'], 'custom text')

    def test_rebinding_candidates_disabled_and_invalid_data_reject_old_actions(self):
        event = self.event('combo', {'item_id': self.node('combo').children[1].ui.id})
        self.runtime.app.choices[1] = ('same', 'replacement')
        self.refresh()
        self.assertEqual(self.runtime.action('event', event)[0], 'stale')
        event = self.event('combo', {'item_id': self.node('combo').children[1].ui.id})
        self.runtime.app.disabled = True
        self.refresh()
        self.assertEqual(self.runtime.action('event', event)[0], 'stale')
        self.assertEqual(self.runtime.action('event', self.event('flag', {'checked': 1}))[0], 'invalid')
        old = self.event('radio', {})
        self.runtime.app.state = State()
        for key, value in dict(flag=False, items=[], mapping={}, radio=None, index=-1, value=None).items():
            setattr(self.runtime.app.state, key, value)
        self.refresh()
        self.assertEqual(self.runtime.action('event', old)[0], 'stale')

    def test_edit_context_change_revokes_draft_and_normalized_binding_is_read_back(self):
        class Uppercase:
            def __init__(self):
                self._value = ''
            @property
            def value(self):
                return self._value
            @value.setter
            def value(self, value):
                self._value = str(value).upper()
        self.runtime.app.free = Uppercase()
        self.refresh()
        self.apply('free', {'value': 'mixed', 'edit_seq': 1, 'composing': False})
        self.assertEqual(self.node('free').properties()['text'], 'MIXED')
        self.runtime.app.editable = True
        self.refresh()
        event = self.event('combo', {'value': 'same', 'edit_seq': 1, 'composing': False})
        self.runtime.app.choices.reverse()
        self.refresh()
        self.assertEqual(self.runtime.action('event', event)[0], 'stale')
