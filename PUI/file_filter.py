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
        if ext == '*':
            pattern = '*'
        elif not ext or any(c in ext for c in '*?[]/\\;|()') or any(c.isspace() for c in ext):
            raise ValueError(f'Invalid file extension: {value!r}')
        else:
            pattern = '*.' + ext
        if pattern not in result:
            result.append(pattern)
    return result


def groups(types):
    """Return (label, patterns) pairs; retain legacy Qt/wx glob strings."""
    if not types:
        return []
    if isinstance(types, Mapping):
        return [(str(label), _extensions(values)) for label, values in types.items()]
    if isinstance(types, (list, tuple)):
        return [('Files', _extensions(types))]
    if not isinstance(types, str):
        raise TypeError('types must be a filter string, extension list, or mapping')
    parts = types.replace(';;', '|').split('|')
    if all('(' in part and part.endswith(')') for part in parts):
        return [(label.strip(), patterns[:-1].split())
                for label, patterns in (part.rsplit('(', 1) for part in parts)]
    if len(parts) % 2:
        raise ValueError('File filters require label/pattern pairs')
    return [(parts[i], parts[i+1].replace(';', ' ').split()) for i in range(0, len(parts), 2)]


def patterns(types):
    return list(dict.fromkeys(p for _, values in groups(types) for p in values))


def qt_filter(types):
    return ';;'.join(f'{label} ({" ".join(values)})' for label, values in groups(types))


def wx_filter(types):
    return '|'.join(part for label, values in groups(types) for part in (label, ';'.join(values)))


def tk_filter(types):
    return [(label, tuple(values)) for label, values in groups(types)] or [('All files', '*')]


def flet_extensions(types):
    values = patterns(types)
    if not values or '*' in values or '*.*' in values:
        return None
    result = []
    for pattern in values:
        if not pattern.startswith('*.') or any(c in pattern[2:] for c in '*?[]'):
            raise ValueError('Flet file filters support extensions only, not arbitrary glob patterns')
        result.append(pattern[2:])
    return result
