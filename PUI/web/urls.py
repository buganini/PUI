"""Public URLs and upstream route paths for a reverse-proxied Web application."""
from urllib.parse import quote, unquote


def _path(value):
    if not isinstance(value, str) or not value.startswith('/'):
        raise ValueError('URL paths must start with /')
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError('URL paths must not contain control characters')
    if any(char in value for char in '\\?#'):
        raise ValueError('URL paths must not contain backslashes, queries or fragments')
    decoded = unquote(value, encoding='utf-8', errors='strict')
    if decoded.count('/') != value.count('/') or '%' in decoded or '\\' in decoded:
        raise ValueError('Encoded separators and double-encoded paths are unsupported')
    if any(ord(char) < 32 or ord(char) == 127 for char in decoded):
        raise ValueError('URL paths must not contain encoded control characters')
    parts = decoded.strip('/').split('/') if decoded != '/' else []
    if '//' in decoded or any(part in ('', '.', '..') for part in parts):
        raise ValueError('URL paths must not contain empty or dot segments')
    return quote(decoded.rstrip('/'), safe='/-._~') + '/'


def _relative_path(value):
    if not isinstance(value, str) or not value or value.startswith('/'):
        raise ValueError('Endpoint paths must be nonempty and relative')
    return _path('/' + value)[1:].rstrip('/')


class WebURLs:
    """Page-relative public URLs, independent of the upstream route mount.

    A proxy may preserve or replace the mount without changing public links.
    It must normalize the public entry to end in / and rewrite cookie paths
    when its public prefix differs from the upstream mount.
    """

    def __init__(self, *, mount_path=None):
        self.mount_path = _path('/' if mount_path is None else mount_path)

    def public(self, endpoint):
        """Return a URL relative to the application entry page."""
        return _relative_path(endpoint)

    def route(self, endpoint):
        """Return the path matched by the upstream HTTP server."""
        return self.mount_path + _relative_path(endpoint)

    def websocket(self):
        return self.public('pui/ws')

    def asset(self, build, filename):
        build = _relative_path(build)
        if '/' in build:
            raise ValueError('Asset build must be one path segment')
        return self.public('assets/' + build + '/' + _relative_path(filename))
