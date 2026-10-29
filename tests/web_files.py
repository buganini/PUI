"""SaveFile paths, cancellations and root confinement without a browser."""
from pathlib import Path
import tempfile
import unittest
from PUI.web.files import DownloadStore, FilePicker, resolve_webroot


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.downloads = DownloadStore(self.root / 'downloads')
        self.addCleanup(self.downloads.close)
        self.picker = FilePicker(resolve_webroot(self.root), downloads=self.downloads)

    def select(self, replies, **kwargs):
        self.steps = []
        answers = iter(replies)
        def ask(kind, message, title, default, options):
            self.steps.append(options)
            return next(answers)
        return self.picker.save(ask, **kwargs)

    def answer(self, action, value=''):
        return dict(action=action, value=value)

    def test_download_allocates_unique_paths_without_creating_file(self):
        paths = [Path(self.select([self.answer('download'), self.answer('confirm', 'report.txt')])) for _ in range(2)]
        self.assertNotEqual(*paths)
        for path in paths:
            self.assertTrue(path.parent.is_dir())
            self.assertFalse(path.exists())
            self.assertTrue(path.is_relative_to(self.downloads.root))
        self.downloads.close()
        self.assertFalse(self.downloads.root.exists())

    def test_metadata_discovery_and_scoped_size_polling(self):
        from unittest.mock import patch
        first = Path(self.downloads.allocate('one.txt'))
        second = Path(self.downloads.allocate('two.txt'))
        first.write_text('one')
        second.write_text('two')
        with patch.object(self.downloads, 'open', wraps=self.downloads.open) as opened:
            self.assertEqual(len(self.downloads.entries(include_size=False)), 2)
            opened.assert_not_called()
            records = self.downloads.entries([first.parent.name])
            self.assertEqual(records[0]['size'], 3)
            opened.assert_called_once_with(first.parent.name)

    def test_cancel_at_every_stage(self):
        existing = self.root / 'existing.txt'
        existing.write_text('keep')
        for replies in ([None], [self.answer('download'), None], [self.answer('save'), None],
                        [self.answer('save'), self.answer('confirm', existing.name), None]):
            self.assertIsNone(self.select(replies))
        self.assertEqual(existing.read_text(), 'keep')
        self.assertFalse(self.downloads.root.exists())

    def test_navigation_and_overwrite(self):
        folder = self.root / 'folder'
        folder.mkdir()
        existing = folder / 'existing.txt'
        existing.write_text('keep')
        result = self.select([self.answer('save'), self.answer('browse', str(folder)),
                              self.answer('confirm', existing.name), self.answer('confirm')])
        self.assertEqual(result, str(existing))
        self.assertEqual(existing.read_text(), 'keep')
        self.assertEqual([s['stage'] for s in self.steps], ['choice', 'browse', 'browse', 'overwrite'])

    def test_parent_and_symlink_escape_rejected(self):
        (self.root / 'escape').symlink_to(self.root.parent, target_is_directory=True)
        self.assertEqual(self.picker.listing(self.root, [])['entries'], [])
        for target in (self.root.parent, self.root / 'escape'):
            self.assertIsNone(self.select([self.answer('save'), self.answer('browse', str(target)), None]))
            self.assertIn('outside webroot', self.steps[-1]['error'])
        self.assertIsNone(self.select([self.answer('download'), self.answer('confirm', '../bad'), None]))
        self.assertIn('without a directory', self.steps[-1]['error'])

    def test_symlink_destination_escape_rejected(self):
        (self.root / 'file.txt').symlink_to(self.root.parent / 'outside.txt')
        self.assertIsNone(self.select([self.answer('save'), self.answer('confirm', 'file.txt'), None]))
        self.assertIn('outside webroot', self.steps[-1]['error'])

    def test_unrestricted_start_and_filter(self):
        self.assertEqual(FilePicker(start=self.root).path('..'), self.root.parent)
        (self.root / 'a.txt').touch()
        (self.root / 'b.png').touch()
        for types in (['txt'], {'Text': ['txt']}):
            self.select([self.answer('save'), None], types=types)
            self.assertEqual([e['name'] for e in self.steps[-1]['entries']], ['a.txt'])
            self.assertEqual(self.steps[-1]['filter'], '*.txt')

    def test_string_filter_rejected_before_save_choice(self):
        with self.assertRaises(TypeError):
            self.select([], types='Text (*.txt)')
        self.assertEqual(self.steps, [])


if __name__ == '__main__':
    unittest.main()
