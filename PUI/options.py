"""String application input from the host environment or Web connection."""
import logging
import os
import re
from urllib.parse import unquote

Options = {}


def load_environment():
    """Load PUI_OPTIONS when a non-Web backend is imported."""
    values = {}
    for part in os.environ.get('PUI_OPTIONS', '').split('#'):
        if not part:
            continue
        try:
            name, separator, value = part.partition('=')
            if not name or not separator or re.search(r'%(?![0-9a-fA-F]{2})', part):
                raise ValueError('Expected percent-encoded name=value')
            name = unquote(name, errors='strict')
            value = unquote(value, errors='strict')
            values[name] = value
        except ValueError as error:
            logging.getLogger('PUI').warning('Skipping invalid PUI_OPTIONS entry: %s', error)
    Options.clear()
    Options.update(values)
