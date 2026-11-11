"""Container spacing validation; Grid uses (row, column) order."""
from math import isfinite
from numbers import Real


def gap_value(value, *, pair=False, terminal=False):
    values = value if pair and isinstance(value, (tuple, list)) else (value, value) if pair else (value,)
    if len(values) != (2 if pair else 1):
        raise ValueError('Grid gap must be a number or a (row, column) pair')
    for item in values:
        if isinstance(item, bool) or not isinstance(item, Real) or not isfinite(item) or item < 0:
            raise ValueError('gap must contain finite nonnegative numbers')
        if terminal and int(item) != item:
            raise ValueError('tGap must use whole character cells')
    return tuple(values) if pair else values[0]
