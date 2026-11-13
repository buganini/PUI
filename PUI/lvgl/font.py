from .base import ffi, lib

_SIZES = (8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48)
_cache = {}


def _font(name):
    font = _cache.get(name)
    if font is None:
        font = _cache[name] = ffi.addressof(lib, name)
    return font


def font_for_size(points):
    """Closest built-in Montserrat bitmap font to a point size at 96 dpi."""
    pixels = (int(points) * 4 + 1) // 3
    size = min(_SIZES, key=lambda s: abs(s - pixels))
    return _font(f'lv_font_montserrat_{size}')


def _bold_fonts():
    return _font('cppui_font_montserrat_bold_14'), _font('cppui_font_montserrat_bold_28')


def is_bold(font):
    return font in _bold_fonts()


def with_weight(font, bold):
    """Bold uses the bold Montserrat (14 or 28) closest in line height;
    regular maps a bold font back to its regular face (as in CPPUI)."""
    bold14, bold28 = _bold_fonts()
    if bold:
        if font in (bold14, bold28):
            return font
        height = font.line_height
        return bold14 if abs(height - bold14.line_height) <= abs(height - bold28.line_height) else bold28
    if font == bold14:
        return _font('lv_font_montserrat_14')
    if font == bold28:
        return _font('lv_font_montserrat_28')
    return font


def resolve(obj, size, weight):
    """Font for a widget's fontSize/fontWeight styles (either may be None)."""
    font = font_for_size(size) if size is not None else lib.lv_obj_get_style_text_font(obj, 0)
    if weight is not None:
        font = with_weight(font, weight >= 600)
    return font
