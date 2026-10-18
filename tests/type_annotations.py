"""Annotations must not change signatures or load optional backends."""
import inspect
import subprocess
import sys
import unittest
from PUI.node import PUINode
from PUI.interfaces import BaseTableAdapter


class AnnotationTests(unittest.TestCase):
    def test_fluent_methods_keep_defaults_and_return_identity(self):
        node = PUINode()
        self.assertIs(node.visible(False).style(fontSize=12).layout(padding=(1, 2)), node)
        self.assertEqual(inspect.signature(PUINode.visible).parameters['value'].default, True)
        self.assertIsNot(inspect.signature(PUINode.style).return_annotation, inspect.Signature.empty)
        self.assertEqual(BaseTableAdapter().editable(0, 0), False)

    def test_core_annotations_do_not_import_backends(self):
        subprocess.run([sys.executable, '-c', '''
import sys
import PUI
import PUI._typing
assert not any(name in sys.modules for name in ('PySide6', 'wx', 'flet', 'textual', 'tkinter', 'aiohttp'))
'''], check=True)
