"""Backend-independent path grammar and validation."""
from enum import Enum
import math


class PathOp(Enum):
    MoveTo = 'M'
    LineTo = 'L'
    QuadTo = 'Q'
    CubicTo = 'C'
    Close = 'Z'


class FillRule(Enum):
    NonZero = 'nonzero'
    EvenOdd = 'evenodd'


def path_commands(path):
    result = []
    started = False
    for item in path:
        if len(result) >= 20000:
            raise ValueError('Path exceeds 20000 commands')
        if not item or not isinstance(item[0], PathOp):
            raise ValueError('Path commands require Canvas.PathOp')
        op, *values = item
        if len(values) != {'M': 2, 'L': 2, 'Q': 4, 'C': 6, 'Z': 0}[op.value]:
            raise ValueError('Invalid path command arity')
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 1e9 for v in values):
            raise ValueError('Path coordinates must be finite and bounded by 1e9')
        if op is PathOp.MoveTo:
            started = True
        elif not started:
            raise ValueError('Path must start with MoveTo')
        result.append((op.value, *values))
    return result


def fill_rule(value):
    if not isinstance(value, FillRule):
        raise ValueError('fillRule must be Canvas.FillRule')
    return value.value
