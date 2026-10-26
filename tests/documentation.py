"""Documentation source moves must preserve the published HTML entry points."""
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class DocumentationBuild(unittest.TestCase):
    def test_pages_keeps_html_urls_and_rewrites_package_source_links(self):
        spec = importlib.util.spec_from_file_location(
            'build_pyodide_docs', ROOT / 'PUI/cookbook/build_pyodide.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with patch.object(builder, 'OUTPUT', output):
                builder.build()
            self.assertIn('href="doc/Reference.html"', (output / 'index.html').read_text())
            for name in ('Reference.html', 'Layout.html'):
                source = (ROOT / 'PUI/doc' / name).read_text()
                built = (output / 'doc' / name).read_text()
                self.assertEqual(re.findall(r'id="([^"]+)"', source),
                                 re.findall(r'id="([^"]+)"', built))
                for link in re.findall(r'href="([^"]+)"', built):
                    if '://' not in link and not link.startswith('#'):
                        self.assertTrue((output / 'doc' / link.split('#')[0]).exists(), link)
            reference = (output / 'doc/Reference.html').read_text()
            self.assertIn('https://github.com/buganini/PUI/blob/main/PUI/doc/web-reference.md', reference)
            self.assertIn('https://github.com/buganini/PUI/blob/main/PUI/cookbook/adaptive.py', reference)

    def test_package_documentation_local_links_exist(self):
        for source in (ROOT / 'PUI/doc').iterdir():
            text = source.read_text()
            for match in re.findall(r'\]\(([^\s)]+)\)|href=["\']([^"\']+)["\']', text):
                link = next(part for part in match if part)
                if '://' in link or link.startswith(('#', 'mailto:')):
                    continue
                self.assertTrue((source.parent / link.split('#')[0]).exists(),
                                '{}: {}'.format(source.name, link))


if __name__ == '__main__':
    unittest.main()
