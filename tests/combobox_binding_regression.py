import unittest
from types import SimpleNamespace
from PUI.common import combobox_get, combobox_set_text, combobox_record_selection
from PUI.state import DummyBinding


class ComboBoxBindingRegression(unittest.TestCase):
    def test_free_text_and_uncontrolled_keyed_selection(self):
        items = [SimpleNamespace(key='a', text='First', value='one'),
                 SimpleNamespace(key='b', text='Second', value='two')]
        state = {'key': None, 'text': ''}
        index = DummyBinding(0)
        combobox_set_text(index, None, 'typed', state)
        self.assertEqual(combobox_get(items, index, None, True, state), (-1, 'typed'))
        combobox_record_selection(items, 1, state)
        self.assertEqual(combobox_get(list(reversed(items)), state=state), (0, 'Second'))
        self.assertEqual(combobox_get(items, text_model=DummyBinding('two')), (1, 'Second'))
