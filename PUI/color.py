"""Backward-compatible TRGB integers; public alpha uses opacity (0..1)."""
import math


def Color(rgb: int, alpha: float = 1) -> int:
    if type(rgb) is not int or not 0 <= rgb <= 0xFFFFFF:
        raise ValueError('rgb must be an integer from 0x000000 to 0xFFFFFF')
    if not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError('alpha must be finite and between 0 and 1')
    return (round((1 - alpha) * 255) << 24) | rgb


def rgba(value):
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError('color must be a TRGB integer from 0 to 0xFFFFFFFF')
    return (value >> 16 & 255, value >> 8 & 255, value & 255, 255 - (value >> 24))


def css_color(value):
    r, g, b, a = rgba(value)
    return f'#{r:02x}{g:02x}{b:02x}' if a == 255 else f'#{r:02x}{g:02x}{b:02x}{a:02x}'


def rgb_color(value):
    """Native RGB-only widgets accept TRGB, but cannot display its opacity."""
    r, g, b, _ = rgba(value)
    return f'#{r:02X}{g:02X}{b:02X}'
