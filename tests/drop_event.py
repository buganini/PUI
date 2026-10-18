import tempfile
from pathlib import Path
import unittest
from types import SimpleNamespace
from PUI.drop import DropEvent, DropFile, dispatch, extensions
from PUI._browser.uploads import UploadStore


class DropTests(unittest.TestCase):
    def test_explicit_accept_and_filter(self):
        node = SimpleNamespace(destroyed=False, _drop_extensions=('.txt',), _onDropped=(lambda e:e.accept(), (), {}))
        node.get_node = lambda: node
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'a.TXT';path.write_text('data')
            self.assertTrue(dispatch(node,DropEvent(files=[DropFile(path.name,str(path))])).accepted)
            event=dispatch(node,DropEvent(files=[DropFile('bad.exe',str(path))]))
            self.assertFalse(event.accepted)
            self.assertTrue(path.exists())
        node._onDropped=(lambda e:None,(),{})
        self.assertFalse(dispatch(node,DropEvent(text='x')).accepted)
        self.assertEqual(extensions(('.TXT','.txt')),('.txt',))

    def test_store_limits_cleanup_and_one_shot_delivery(self):
        store=UploadStore(upload_limits=dict(max_files=2,max_file_bytes=4,max_session_bytes=6))
        try:
            key=store.begin();fid=store.add(key,'a.txt')
            store.write(key,fid,b'abcd')
            with self.assertRaises(ValueError):store.write(key,fid,b'e')
            fid2=store.add(key,'b.txt');store.write(key,fid2,b'ab')
            with self.assertRaises(ValueError):store.add(key,'c.txt')
            with self.assertRaises(ValueError):store.write(key,fid2,b'c')
            store.finish(key);files=store.take(key)
            self.assertTrue(all(f.temporary for f in files))
            with self.assertRaises(FileNotFoundError):store.take(key)
            Path(files[0].path).unlink()
            self.assertEqual(store.usage(),2)
            store.discard(key);store.discard(key)
        finally:store.close();store.close()
        self.assertFalse(store.root.exists())

    def test_directory_filter(self):
        node = SimpleNamespace(destroyed=False, _drop_extensions=extensions(('.txt', '/')),
                               _onDropped=(lambda e: e.accept(), (), {}))
        node.get_node = lambda: node
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / 'folder.txt'
            directory.mkdir()
            file = Path(root) / 'a.txt'
            file.write_text('hello')
            entries = [DropFile(p.name, str(p)) for p in (directory, file)]
            self.assertTrue(dispatch(node, DropEvent(files=entries)).accepted)
            node._drop_extensions = ('.txt',)
            self.assertFalse(dispatch(node, DropEvent(files=entries)).accepted)
            node._drop_extensions = ('/',)
            self.assertFalse(dispatch(node, DropEvent(files=entries)).accepted)
            self.assertTrue(dispatch(node, DropEvent(files=entries[:1])).accepted)
            node._drop_extensions = None
            self.assertTrue(dispatch(node, DropEvent(files=entries)).accepted)
            self.assertTrue(directory.is_dir())
        for invalid in ('/tmp', '.txt/', ''):
            with self.assertRaises(ValueError):
                extensions(invalid)
