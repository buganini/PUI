import unittest
from PUI.file_filter import groups, patterns, qt_filter, wx_filter, tk_filter, flet_extensions


class FileFilters(unittest.TestCase):
    def test_structured_formats(self):
        expected = [('Images', ['png', 'jpg']), ('Text', ['txt'])]
        for value in ({'Images': ['png', '.jpg'], 'Text': ['txt']},):
            self.assertEqual(groups(value), expected)
            self.assertEqual(qt_filter(value), 'Images (*.png *.jpg);;Text (*.txt)')
            self.assertEqual(wx_filter(value), 'Images|*.png;*.jpg|Text|*.txt')
            self.assertEqual(tk_filter(value), [('Images', ('*.png', '*.jpg')), ('Text', ('*.txt',))])
            self.assertEqual(flet_extensions(value), ['png', 'jpg', 'txt'])
            self.assertEqual(patterns(value), ['*.png', '*.jpg', '*.txt'])

    def test_extensions_and_all_files(self):
        self.assertEqual(groups(['txt', '.txt', 'tar.gz']), [('Files', ['txt', 'tar.gz'])])
        self.assertEqual(patterns(['txt', '.txt', 'tar.gz']), ['*.txt', '*.tar.gz'])
        self.assertEqual(flet_extensions({'A': ['txt'], 'B': ['.txt', 'tar.gz']}), ['txt', 'tar.gz'])
        for value in (None, [], {}, ['*'], {'All': ['*']}):
            self.assertIsNone(flet_extensions(value))
        self.assertEqual(qt_filter(None), '')
        self.assertEqual(tk_filter(None), [('All files', '*')])

    def test_invalid_extensions_and_rejected_strings(self):
        for value in (['*.txt'], [''], ['a/b'], ['a?'], [42], {'Text': []}):
            with self.assertRaises(ValueError):
                groups(value)
        for value in ('', 'Text (*.txt)', 'Text|*.txt',
                      'Kikakuka FabPlan (*.kkkk_fab)|*.kkkk_fab', False, 0):
            for convert in (groups, patterns, qt_filter, wx_filter, tk_filter, flet_extensions):
                with self.subTest(value=value, convert=convert.__name__), self.assertRaises(TypeError):
                    convert(value)
