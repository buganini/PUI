"""Copy the static site and zip the Python sources for the Pyodide cookbook."""
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'dist' / 'pyodide'


def build():
    assets = OUTPUT / 'cookbook' / 'pyodide'
    assets.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(assets / 'app.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for folder in ('PUI', 'PUI/_browser', 'PUI/pyodide', 'PUI/cookbook'):
            for source in (ROOT / folder).glob('*.py'):
                archive.write(source, source.relative_to(ROOT))
        for name in ('PUI/cookbook/assets/windmill.jpg', 'PUI/cookbook/assets/ATTRIBUTION.md', 'LICENSE.txt'):
            archive.write(ROOT / name, name)

    shutil.copyfile(ROOT / 'PUI' / 'cookbook' / 'cookbook.html', OUTPUT / 'cookbook' / 'cookbook.html')
    shutil.copyfile(ROOT / 'PUI' / 'cookbook' / 'index.html', OUTPUT / 'index.html')
    (OUTPUT / 'doc').mkdir(exist_ok=True)
    for source in (ROOT / 'PUI' / 'doc').glob('*.html'):
        # Package-local links are useful offline. On Pages, keep HTML documents
        # at their established /doc/ URLs and send source/Markdown links to GitHub.
        def published_link(match):
            url = match.group(2)
            if url.startswith(('#', '/', 'https:', 'http:', 'mailto:')):
                return match.group(0)
            path, separator, fragment = url.partition('#')
            target = (source.parent / path).resolve()
            if target.parent == source.parent and target.suffix == '.html':
                return match.group(0)
            relative = target.relative_to(ROOT).as_posix()
            published = 'https://github.com/buganini/PUI/blob/main/' + relative
            if separator:
                published += '#' + fragment
            return match.group(1) + published + match.group(3)

        content = re.sub(r'(href=["\'])([^"\']+)(["\'])', published_link,
                         source.read_text(encoding='utf-8'))
        (OUTPUT / 'doc' / source.name).write_text(content, encoding='utf-8')
    shutil.copyfile(ROOT / 'LICENSE.txt', OUTPUT / 'LICENSE.txt')
    (OUTPUT / '.nojekyll').touch()


if __name__ == '__main__':
    build()
