from .base import ffi, lib

_SIZES = (8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48)
_cache = {}


def font_for_size(points):
    """Closest built-in Montserrat bitmap font to a point size at 96 dpi."""
    pixels = (int(points) * 4 + 1) // 3
    size = min(_SIZES, key=lambda s: abs(s - pixels))
    font = _cache.get(size)
    if font is None:
        font = _cache[size] = ffi.addressof(lib, f'lv_font_montserrat_{size}')
    return font
