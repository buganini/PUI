"""Signature discoverability and compatibility, without native windows."""
import importlib.util
import inspect
import unittest

from PUI import PUIView, State, StateList
from PUI.dom import recur_delete


class StateSignatureTests(unittest.TestCase):
    def test_sort_options_and_notifications(self):
        values = State(['aa', 'b', 'ccc'])
        changes = []

        class Observer(PUIView):
            def content(self):
                changes.append(list(values))

        observer = Observer()
        self.addCleanup(recur_delete, observer, observer, True)
        observer.sync()
        changes.clear()
        values.sort(key=len, reverse=True)
        self.assertEqual(list(values), ['ccc', 'aa', 'b'])
        self.assertEqual(changes, [['ccc', 'aa', 'b']])
        values.sort()
        self.assertEqual(list(values), ['aa', 'b', 'ccc'])
        with self.assertRaises(TypeError):
            values.sort(None)
        signature = inspect.signature(values.sort)
        for name in ('key', 'reverse'):
            self.assertEqual(signature.parameters[name].kind,
                             inspect.Parameter.KEYWORD_ONLY)
        self.assertIsNone(signature.parameters['key'].default)
        self.assertIs(signature.parameters['reverse'].default, False)

    def test_custom_sort_receives_defaults_and_extra_arguments(self):
        class Collection(list):
            def sort(self, *args, **kwargs):
                self.received = args, kwargs

        backing = Collection([1])
        values = StateList(backing)
        values.sort()
        self.assertEqual(backing.received, ((), {'key': None, 'reverse': False}))
        values.sort('custom', key=None, reverse=False, algorithm='stable')
        self.assertEqual(backing.received,
                         (('custom',), {'key': None, 'reverse': False,
                                       'algorithm': 'stable'}))

    def test_index_keeps_keyword_value_and_positional_bounds(self):
        values = State(['a', 'b', 'a'])
        self.assertEqual(values.index(value='a'), 0)
        self.assertEqual(values.index('a', 1, 3), 2)
        with self.assertRaises(TypeError):
            values.index('a', start=1)


@unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 unavailable')
class QtSignatureTests(unittest.TestCase):
    def test_named_options_preserve_omissions_none_and_extensions(self):
        from PUI.PySide6.base import QtBaseWidget, QtPUIView
        for cls in (QtBaseWidget, QtPUIView):
            with self.subTest(cls=cls):
                node = cls()
                try:
                    self.assertIs(node.qt(Style='fusion', StyleSheet={'color': 'red'},
                                          custom='value'), node)
                    node.qt(HorizontalPolicy=1).qt()
                    self.assertEqual(node.qt_params, {
                        'Style': 'fusion', 'StyleSheet': {'color': 'red'},
                        'HorizontalPolicy': 1, 'custom': 'value',
                    })
                    node.qt(Style=None, StyleSheet={})
                    self.assertEqual(node.qt_params['Style'], 'fusion')
                    self.assertEqual(node.qt_params['StyleSheet'], {})
                    for name in ('Style', 'HorizontalPolicy', 'VerticalPolicy',
                                 'SizeConstraint', 'StyleSheet'):
                        parameter = inspect.signature(node.qt).parameters[name]
                        self.assertEqual(parameter.kind, inspect.Parameter.KEYWORD_ONLY)
                        self.assertIsNone(parameter.default)
                finally:
                    node.destroy(True)


if __name__ == '__main__':
    unittest.main()
