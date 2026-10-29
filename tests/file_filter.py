import unittest
from PUI.file_filter import groups, patterns, qt_filter, wx_filter, tk_filter, flet_extensions
from PUI._browser.file_selection import filters


class FileFilters(unittest.TestCase):
    def test_structured_and_legacy_formats(self):
        expected = [('Images', ['*.png', '*.jpg']), ('Text', ['*.txt'])]
        for value in ({'Images': ['png', '.jpg'], 'Text': ['txt']},
                      'Images (*.png *.jpg);;Text (*.txt)',
                      'Images|*.png;*.jpg|Text|*.txt'):
            self.assertEqual(groups(value), expected)
            self.assertEqual(qt_filter(value), 'Images (*.png *.jpg);;Text (*.txt)')
            self.assertEqual(wx_filter(value), 'Images|*.png;*.jpg|Text|*.txt')
            self.assertEqual(tk_filter(value), [('Images', ('*.png', '*.jpg')), ('Text', ('*.txt',))])
            self.assertEqual(flet_extensions(value), ['png', 'jpg', 'txt'])
            self.assertEqual(filters(value), ['*.png', '*.jpg', '*.txt'])

    def test_extensions_and_all_files(self):
        self.assertEqual(patterns(['txt', '.txt', 'tar.gz']), ['*.txt', '*.tar.gz'])
        for value in (None, [], {}, ['*'], {'All': ['*']}, 'All (*.*)'):
            self.assertIsNone(flet_extensions(value))
        self.assertEqual(qt_filter(None), '')
        self.assertEqual(tk_filter(None), [('All files', '*')])

    def test_invalid_extensions_and_legacy_globs(self):
        for value in (['*.txt'], [''], ['a/b'], ['a?'], [42], {'Text': []}):
            with self.assertRaises(ValueError):
                groups(value)
        self.assertEqual(patterns('Report|report-?.txt'), ['report-?.txt'])
        with self.assertRaises(ValueError):
            flet_extensions('Report|report-?.txt')
