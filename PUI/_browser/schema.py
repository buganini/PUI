"""Transport-independent browser data limits and validation."""
from dataclasses import dataclass
import math

SAFE_INTEGER = 2 ** 53 - 1


class ProtocolError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class RenderLimits:
    max_decoded_bytes: int = 32 * 1024 * 1024
    max_items: int = 5000000
    max_depth: int = 64

    def __post_init__(self):
        for value in self.__dict__.values():
            if type(value) is not int or value <= 0:
                raise ValueError('Protocol limits must be positive integers')


def validate_data(value, *, limits=None, check_numbers=True):
    """Check the wire value subset without converting opaque Python objects."""
    limits = limits or RenderLimits()
    remaining = limits.max_items
    byte_budget = limits.max_decoded_bytes

    def visit(item, depth):
        nonlocal remaining, byte_budget
        remaining -= 1
        if remaining < 0:
            raise ProtocolError('LIMIT_EXCEEDED',
                'Value count exceeds limit (%s > %s)' % (limits.max_items - remaining, limits.max_items))
        if depth > limits.max_depth:
            raise ProtocolError('LIMIT_EXCEEDED',
                'Nesting depth exceeds limit (%s > %s)' % (depth, limits.max_depth))
        kind = type(item)
        if item is None or kind is bool:
            return
        if kind is int:
            if check_numbers and abs(item) > SAFE_INTEGER:
                raise ProtocolError('INVALID_VALUE', 'Integer exceeds exact JavaScript range')
        elif kind is float:
            if check_numbers and not math.isfinite(item):
                raise ProtocolError('INVALID_VALUE', 'Non-finite number')
        elif kind in (str, bytes):
            try:
                byte_budget -= len(item.encode('utf-8') if kind is str else item)
            except UnicodeError as error:
                raise ProtocolError('INVALID_VALUE', 'Invalid Unicode') from error
            if byte_budget < 0:
                raise ProtocolError('LIMIT_EXCEEDED', 'Value bytes exceed limit')
        elif kind in (list, tuple):
            for child in item:
                visit(child, depth + 1)
        elif kind is dict:
            for key, child in item.items():
                if type(key) is not str or key == '__proto__':
                    raise ProtocolError('INVALID_VALUE', 'Invalid map key')
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            raise ProtocolError('INVALID_VALUE', 'Unsupported wire value type: ' + kind.__name__)

    visit(value, 0)
