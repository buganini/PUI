"""Builder metadata, source discovery, and deferred argument forwarding."""
import importlib
import importlib.util
import inspect
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

from PUI import PUIView


class DecoratorSignatureTests(unittest.TestCase):
    def decorators(self):
        for name in ('PUI', 'PUI.PySide6', 'PUI.wx', 'PUI.tkinter',
                     'PUI.flet', 'PUI.textual'):
            if '.' in name and importlib.util.find_spec(name.split('.')[1]) is None:
                continue
            module = importlib.import_module(name)
            for decorator_name in ('PUI', 'PUIApp'):
                decorator = getattr(module, decorator_name, None)
                if decorator is not None:
                    yield name, decorator_name, decorator

    def test_metadata_source_and_argument_forwarding(self):
        for module, name, decorator in self.decorators():
            with self.subTest(module=module, decorator=name):
                calls = []

                def builder(first: str, /, second=2, *items, enabled=True, **options):
                    """Builder documentation visible through the decorator."""
                    calls.append((first, second, items, enabled, options))

                wrapped = decorator(builder)
                self.assertIs(wrapped.__wrapped__, builder)
                self.assertIs(inspect.unwrap(wrapped), builder)
                self.assertEqual(inspect.signature(wrapped), inspect.signature(builder))
                for attribute in ('__name__', '__qualname__', '__module__',
                                  '__doc__', '__annotations__'):
                    self.assertEqual(getattr(wrapped, attribute), getattr(builder, attribute))
                self.assertEqual(inspect.getsource(inspect.unwrap(wrapped)),
                                 inspect.getsource(builder))
                for args, kwargs, expected in (
                    (('first',), {}, ('first', 2, (), True, {})),
                    (('first', 3, 'tail'), {'enabled': False, 'color': 'red'},
                     ('first', 3, ('tail',), False, {'color': 'red'})),
                    (('first',), {'second': 4}, ('first', 4, (), True, {})),
                ):
                    previous_calls = len(calls)
                    node = wrapped(*args, **kwargs)
                    try:
                        self.assertIsInstance(node, PUIView)
                        self.assertEqual(len(calls), previous_calls)
                        node.content()
                        self.assertEqual(calls[-1], expected)
                    finally:
                        node.destroy(True)

    def test_bad_builder_arguments_still_fail_when_content_is_built(self):
        for module, name, decorator in self.decorators():
            with self.subTest(module=module, decorator=name):
                def builder(required, *, flag):
                    pass

                node = decorator(builder)()
                try:
                    with self.assertRaises(TypeError):
                        node.content()
                finally:
                    node.destroy(True)

    def test_package_declares_python_39_without_new_dependency(self):
        root = Path(__file__).resolve().parents[1]
        with patch('setuptools.setup') as setup:
            runpy.run_path(str(root / 'setup.py'))
        self.assertEqual(setup.call_args.kwargs['python_requires'], '>=3.9')
        self.assertNotIn('typing_extensions',
                         setup.call_args.kwargs.get('install_requires', []))


if __name__ == '__main__':
    unittest.main()
