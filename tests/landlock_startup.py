"""Run real restrictions in disposable processes, never in the test runner."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PUI._landlock import apply, prepare


class LandlockTests(unittest.TestCase):
    def test_disabled(self):
        apply(None)

    def test_other_platform_warns(self):
        with patch('PUI._landlock.sys.platform', 'darwin'), self.assertLogs('PUI', level='WARNING'):
            self.assertIsNone(prepare({}))

    @unittest.skipUnless(sys.platform == 'linux', 'Linux only')
    def test_invalid_policy(self):
        for policy in ({'deny': []}, {'read': '/tmp'}, True):
            with self.assertRaises(ValueError):
                prepare(policy)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux only')
    def test_filesystem(self):
        try:
            prepare({})
        except (ImportError, RuntimeError, OSError) as error:
            self.skipTest(str(error))
        with tempfile.TemporaryDirectory() as root:
            for name in ('read', 'write', 'outside'):
                folder = Path(root, name)
                folder.mkdir()
                (folder / 'file').write_text('original')
            Path(root, 'write', 'escape').symlink_to(Path(root, 'outside', 'file'))
            code = '''
import os, sys
from PUI._landlock import apply
root = sys.argv[1]
apply({'read': [root+'/read'], 'write': [root+'/write']})
assert open(root+'/read/file').read() == 'original'
with open(root+'/write/file', 'w') as f: f.write('changed')
os.rename(root+'/write/file', root+'/write/renamed')
os.unlink(root+'/write/renamed')
for path, mode in [('read/file','w'), ('outside/file','r'), ('write/escape','r')]:
    try: open(root+'/'+path, mode)
    except PermissionError: pass
    else: raise AssertionError((path, mode))
# Descendants inherit the policy.
pid = os.fork()
if not pid:
    try: open(root+'/outside/file')
    except PermissionError: os._exit(0)
    os._exit(1)
assert os.waitpid(pid, 0)[1] == 0
'''
            result = subprocess.run([sys.executable, '-c', code, root], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux only')
    def test_existing_thread_rejected(self):
        code = '''
import threading
from PUI._landlock import apply
stop = threading.Event()
t = threading.Thread(target=stop.wait)
t.start()
try:
    try: apply({})
    except RuntimeError as e: assert 'background threads' in str(e)
    else: raise AssertionError('restriction accepted')
finally:
    stop.set(); t.join()
'''
        try:
            prepare({})
        except (ImportError, RuntimeError, OSError) as error:
            self.skipTest(str(error))
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
