"""Build a static cookbook from an explicit list of sources/assets; Python 3.9+."""
from pathlib import Path
import re
import shutil
from urllib.parse import urljoin
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'dist' / 'pyodide'


def sources():
    for folder in ('PUI', 'PUI/_browser', 'PUI/pyodide', 'cookbook'):
        for source in sorted((ROOT / folder).glob('*.py')):
            if source.name != 'build_pyodide.py':
                yield source
    yield ROOT / 'screenshots' / 'hello_world.png'
    yield ROOT / 'LICENSE.txt'


def build():
    assets = OUTPUT / 'cookbook' / 'pyodide'
    assets.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(assets / 'app.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources():
            if source.is_symlink():
                raise ValueError('Do not package source symlinks: %s' % source)
            info = zipfile.ZipInfo(source.relative_to(ROOT).as_posix())
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, source.read_bytes())
    shutil.copyfile(ROOT / 'cookbook' / 'cookbook.html', OUTPUT / 'cookbook' / 'cookbook.html')
    # Keep existing static documentation URLs when this artifact is published to Pages.
    (OUTPUT / 'doc').mkdir(exist_ok=True)
    for source in (ROOT / 'doc').glob('*.html'):
        # Keep links to Markdown/source documents readable without a Jekyll build.
        html = re.sub(r'href="([^"?:]+\.(?:md|py|txt)(?:#[^"]*)?)"',
                      lambda match: 'href="%s"' % urljoin(
                          'https://github.com/buganini/PUI/blob/main/doc/', match[1]),
                      source.read_text(encoding='utf-8'))
        (OUTPUT / 'doc' / source.name).write_text(html, encoding='utf-8')
    shutil.copyfile(ROOT / 'LICENSE.txt', OUTPUT / 'LICENSE.txt')
    (OUTPUT / '.nojekyll').write_text('', encoding='utf-8')
    (OUTPUT / 'index.html').write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>PUI</title>'
        '<a href="cookbook/cookbook.html">Open the PUI Cookbook</a>'
        '<p><a href="doc/Reference.html">Components reference</a></p></html>\n', encoding='utf-8')


if __name__ == '__main__':
    build()
