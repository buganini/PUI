"""Shared URL validation and the desktop implementation of OpenURL."""
from urllib.parse import urlsplit


def validate_url(url):
    if not isinstance(url, str):
        raise TypeError('OpenURL expects a URL string')
    if not url or url != url.strip() or len(url) > 8192 or any(ord(c) < 32 or ord(c) == 127 for c in url):
        raise ValueError('OpenURL expects a nonempty URL without control characters')
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in ('http', 'https', 'mailto'):
        raise ValueError('OpenURL supports absolute http, https and mailto URLs')
    if parsed.scheme.lower() in ('http', 'https') and not parsed.hostname:
        raise ValueError('OpenURL requires a host')
    if parsed.scheme.lower() == 'mailto' and not parsed.path:
        raise ValueError('OpenURL requires a mail recipient')
    return url


def OpenURL(url: str) -> None:
    """Ask the system default browser/URL handler to open a URL."""
    import webbrowser
    if not webbrowser.open_new_tab(validate_url(url)):
        raise RuntimeError('No browser accepted the URL')
