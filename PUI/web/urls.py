"""Public URLs and upstream route paths for a reverse-proxied Web application."""
from urllib.parse import quote, unquote, urlsplit, urlunsplit


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
    """Resolve a public base URL separately from the proxy's upstream mount.

    ``mount_path=None`` preserves the public path upstream. Use ``mount_path='/'``
    when a reverse proxy removes the public prefix before forwarding requests.
    Values come from server configuration, never untrusted forwarding headers.
    """

    def __init__(self, base_url='/', *, mount_path=None):
        if not isinstance(base_url, str) or not base_url:
            raise ValueError('base_url must be a root-relative path or HTTP(S) URL')
        if any(ord(char) < 32 or ord(char) == 127 for char in base_url):
            raise ValueError('base_url must not contain control characters')
        parts = urlsplit(base_url)
        if parts.query or parts.fragment or '?' in base_url or '#' in base_url:
            raise ValueError('base_url must not contain a query or fragment')
        if parts.scheme:
            if base_url[0].isspace():
                raise ValueError('Absolute base_url must not have leading whitespace')
            if parts.scheme not in ('http', 'https') or not parts.hostname:
                raise ValueError('Absolute base_url must use HTTP or HTTPS')
            if parts.username is not None or parts.password is not None:
                raise ValueError('base_url must not contain credentials')
            if any(char.isspace() or char == '\\' for char in parts.netloc):
                raise ValueError('Invalid base_url authority')
            parts.port  # Validate a supplied port without changing the authority.
        elif parts.netloc or not base_url.startswith('/'):
            raise ValueError('Relative base_url must start with a single /')
        self.public_path = _path(parts.path or '/')
        self.base_url = urlunsplit((parts.scheme, parts.netloc, self.public_path, '', ''))
        self.mount_path = self.public_path if mount_path is None else _path(mount_path)

    def public(self, endpoint):
        """Return an HTTP(S) or root-relative URL without dropping the prefix."""
        return self.base_url + _relative_path(endpoint)

    def route(self, endpoint):
        """Return the path matched by the upstream HTTP server."""
        return self.mount_path + _relative_path(endpoint)

    def websocket(self):
        """Return a WS(S) URL, or a root-relative path for the page's origin."""
        parts = urlsplit(self.public('pui/ws'))
        scheme = {'http': 'ws', 'https': 'wss', '': ''}[parts.scheme]
        return urlunsplit((scheme, parts.netloc, parts.path, '', ''))

    def asset(self, build, filename):
        """Resolve a packaged asset below the public base URL."""
        build = _relative_path(build)
        if '/' in build:
            raise ValueError('Asset build must be one path segment')
        return self.public('assets/' + build + '/' + _relative_path(filename))
