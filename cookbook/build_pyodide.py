"""Copy the static site and zip the Python sources for the Pyodide cookbook."""
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'dist' / 'pyodide'


def build():
    assets = OUTPUT / 'cookbook' / 'pyodide'
    assets.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(assets / 'app.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for folder in ('PUI', 'PUI/_browser', 'PUI/pyodide', 'cookbook'):
            for source in (ROOT / folder).glob('*.py'):
                archive.write(source, source.relative_to(ROOT))
        for name in ('screenshots/hello_world.png', 'LICENSE.txt'):
            archive.write(ROOT / name, name)

    shutil.copyfile(ROOT / 'cookbook' / 'cookbook.html', OUTPUT / 'cookbook' / 'cookbook.html')
    shutil.copyfile(ROOT / 'cookbook' / 'index.html', OUTPUT / 'index.html')
    (OUTPUT / 'doc').mkdir(exist_ok=True)
    for source in (ROOT / 'doc').glob('*.html'):
        shutil.copyfile(source, OUTPUT / 'doc' / source.name)
    shutil.copyfile(ROOT / 'LICENSE.txt', OUTPUT / 'LICENSE.txt')
    (OUTPUT / '.nojekyll').touch()


if __name__ == '__main__':
    build()
