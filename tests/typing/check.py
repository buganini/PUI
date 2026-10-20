"""Check the public typing examples and verify incorrect calls are rejected."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
checker = Path(sys.executable).with_name('pyrefly')
command = [str(checker), 'check', '--preset', 'default',
           '--python-interpreter-path', sys.executable]
source = Path(__file__).with_name('public_api.py')
subprocess.run(command + [str(source)], cwd=root, check=True)
invalid = '''
from PUI import PySide6 as Qt
from PUI import web as Web
from PUI import textual as Textual
Qt.Button('wrong', disabled='yes')
Web.Label('wrong').visible('yes')
Web.Label('wrong').style(fontSize='large')
Web.Canvas(None)
Qt.Application().start(codex=True)
Web.Application().run(claude="key")
Qt.Application().run(codex={"effort": 123})
Web.Grid().columns(3, dense="true")
Textual.Grid().tColumns(3, dense=1)

def invalid_colors(qt: Qt.Canvas, web: Web.Canvas) -> None:
    from PySide6.QtGui import QColor
    qt.drawLine(0, 0, 1, 1, color=QColor('red'))
    web.drawRect(0, 0, 1, 1, fill='red')
'''
# Keep the temporary fixture beside the valid example for identical import resolution.
with tempfile.NamedTemporaryFile(mode='w', suffix='.py', dir=source.parent) as fixture:
    fixture.write(invalid)
    fixture.flush()
    result = subprocess.run(command + [fixture.name], cwd=root, capture_output=True, text=True)
    output = result.stdout + result.stderr
    if result.returncode == 0 or output.count('[bad-argument-type]') != 11:
        raise AssertionError(output)
print('Public API types and eleven rejected argument cases passed.')
