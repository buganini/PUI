"""python -m unittest discover -s tests -p optional_binding.py -v"""
import unittest

from PUI import State


class OptionalBindingTests(unittest.TestCase):
    def test_clear_preserves_none_and_existing_non_null_conversion(self):
        for initial, text, expected in [('editor', 'settings', 'settings'), (1, '2', 2), (1.0, '2.5', 2.5)]:
            obj = State()
            obj.value = initial
            for state, key in [(obj, 'value'), (State([initial]), 0), (State({'value': initial}), 'value')]:
                with self.subTest(initial=initial, state=type(state).__name__):
                    binding = state(key)
                    binding.value = None
                    self.assertIsNone(binding.value)
                    self.assertIsNone(state(key).value)
                    binding.value = text
                    self.assertEqual(binding.value, expected)


if __name__ == '__main__':
    unittest.main()
