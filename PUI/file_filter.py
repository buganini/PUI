"""Backend-independent file filters and native picker adapters."""
from collections.abc import Mapping


def _extensions(values):
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError('File extensions require a non-empty list')
    result = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError('File extensions must be strings')
        ext = value.removeprefix('.')
        if ext != '*' and (not ext or any(c in ext for c in '*?[]/\\;|()') or any(c.isspace() for c in ext)):
            raise ValueError(f'Invalid file extension: {value!r}')
        if ext not in result:
            result.append(ext)
    return result


def groups(types):
    """Return (label, extensions) pairs from structured extension filters."""
    if types is None:
        return []
    if isinstance(types, Mapping):
        return [(str(label), _extensions(values)) for label, values in types.items()]
    if isinstance(types, (list, tuple)):
        return [('Files', _extensions(types))] if types else []
    raise TypeError('types must be an extension list or mapping, e.g. ["txt"] or {"Text": ["txt"]}; filter strings are no longer supported')


def _pattern(extension):
    return '*' if extension == '*' else '*.' + extension


def patterns(types):
    return list(dict.fromkeys(_pattern(ext) for _, values in groups(types) for ext in values))


def qt_filter(types):
    return ';;'.join(f'{label} ({" ".join(map(_pattern, values))})' for label, values in groups(types))


def wx_filter(types):
    return '|'.join(part for label, values in groups(types) for part in (label, ';'.join(map(_pattern, values))))


def tk_filter(types):
    return [(label, tuple(map(_pattern, values))) for label, values in groups(types)] or [('All files', '*')]


def flet_extensions(types):
    values = list(dict.fromkeys(ext for _, extensions in groups(types) for ext in extensions))
    return None if not values or '*' in values else values
