"""Open a URL in the connected user's browser, never on the Python host."""
from .._url import validate_url
from . import widgets


def OpenURL(url: str) -> None:
    url = validate_url(url)
    runtime = widgets._current_runtime
    if runtime is None or runtime.closed:
        raise RuntimeError('OpenURL requires an active browser runtime')
    runtime.queue_open_url(url)
