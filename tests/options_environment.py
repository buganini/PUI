"""Non-Web imports initialize string Options without parsing application data."""
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from PUI.options import Options, load_environment


class EnvironmentOptionsTests(unittest.TestCase):
    def setUp(self):
        self.previous = dict(Options)

    def tearDown(self):
        Options.clear()
        Options.update(self.previous)

    def test_optional_prefix_decoding_and_last_value_wins(self):
        source = 'a=b#c=d#a=last#empty=#count=00123#flag=true#csv=a,b#text=%E4%B8%96%E7%95%8C%23%3D#plus=a+b#equals=a=b'
        expected = {'a': 'last', 'c': 'd', 'empty': '', 'count': '00123',
                    'flag': 'true', 'csv': 'a,b', 'text': '世界#=',
                    'plus': 'a+b', 'equals': 'a=b'}
        original = Options
        for prefix in ('', '#'):
            with patch.dict(os.environ, {'PUI_OPTIONS': prefix + source}):
                load_environment()
            self.assertIs(Options, original)
            self.assertEqual(Options, expected)

    def test_missing_or_empty_environment_clears_options(self):
        for values in ({}, {'PUI_OPTIONS': ''}):
            Options['old'] = 'value'
            with patch.dict(os.environ, values, clear=True):
                load_environment()
            self.assertEqual(Options, {})

    def test_invalid_entries_leave_valid_values_intact(self):
        with patch.dict(os.environ, {'PUI_OPTIONS': 'a=ok#a=%zz#missing#=empty#bad=%FF#good=null'}):
            with self.assertLogs('PUI', level='WARNING') as messages:
                load_environment()
        self.assertEqual(len(messages.output), 4)
        self.assertEqual(Options, {'a': 'ok', 'good': 'null'})

    def test_backend_imports_load_options_except_web(self):
        for backend in ('PySide6', 'wx', 'tkinter', 'flet', 'textual', 'pyodide', 'web'):
            with self.subTest(backend=backend):
                expected = {} if backend == 'web' else {'a': 'b', 'c': '123'}
                code = f'import PUI; import PUI.{backend}; assert PUI.Options == {expected!r}, PUI.Options'
                subprocess.run([sys.executable, '-c', code], check=True, timeout=30,
                               env=dict(os.environ, PUI_OPTIONS='#a=b#c=123', QT_QPA_PLATFORM='offscreen'))


if __name__ == '__main__':
    unittest.main()
