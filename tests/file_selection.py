from pathlib import Path
import tempfile
import unittest
from PUI._browser.uploads import UploadStore
from PUI.web.files import FilePicker

class FileSelectionTests(unittest.TestCase):
    def setUp(self):
        self.store = UploadStore()
        self.addCleanup(self.store.close)
    def test_directory_structure_and_consumption(self):
        key = self.store.begin()
        for name in ('dataset/a.txt', 'dataset/nested/b.txt'):
            fid = self.store.add_selection(key, name, 'directory', [], 'token')
            self.store.write(key, fid, b'hello')
        self.store.finish(key)
        with self.assertRaises(ValueError):
            self.store.take_selection(key, 'other', 'directory')
        path = Path(self.store.take_selection(key, 'token', 'directory'))
        self.assertEqual((path / 'nested/b.txt').read_bytes(), b'hello')
        self.assertEqual(self.store.usage(), 10)
        self.store.discard_pending()
        self.assertTrue(path.exists())
    def test_paths_duplicates_filters_and_count(self):
        key = self.store.begin()
        for name in ('../x', '/root/x', 'folder/../x', 'C:/x', 'folder//x', 'folder/NUL.txt', 'folder/a\\b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.store.add_selection(key, name, 'directory', [], 't')
        self.store.add_selection(key, 'x.txt', 'file', ['*.txt'], 't')
        with self.assertRaises(ValueError):
            self.store.add_selection(key, 'y.txt', 'file', [], 't')
        key = self.store.begin()
        self.store.add_selection(key, 'x.txt', 'files', ['*.txt'], 't')
        for name in ('X.txt', 'x.png', 'folder/x.txt'):
            with self.assertRaises(ValueError):
                self.store.add_selection(key, name, 'files', ['*.txt'], 't')
    def test_server_selection_rechecks_webroot_and_types(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            root = Path(root).resolve(); (root/'folder').mkdir(); (root/'a.txt').write_text('a')
            (root/'link').symlink_to(outside, target_is_directory=True)
            picker = FilePicker(root)
            answers = iter([{'action':'browse','value':str(root/'link')}, {'action':'open','value':str(root/'a.txt')}])
            errors = []
            def ask(*args):
                errors.append(args[-1]['error'])
                return next(answers)
            self.assertEqual(picker.open(ask, 'file', 'Open', None, 'Text|*.txt', self.store, 't'), str(root/'a.txt'))
            self.assertIn('outside webroot', errors[-1])
