"""Import must happen after the worker's read-only policy is installed."""
import tempfile
from web_fixture import App

try:
    with tempfile.TemporaryFile(dir='/tmp'):
        pass
except PermissionError:
    pass
else:
    raise AssertionError('Worker imported application before applying Landlock')
