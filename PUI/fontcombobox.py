"""Shared font-family choices; a family name is not a font-file path."""
DEFAULT_FONTS = ('sans-serif', 'serif', 'monospace')


def font_choices(fonts):
    if isinstance(fonts, (str, bytes)):
        raise TypeError('fonts must be an iterable of font-family names')
    result = []
    for name in fonts:
        if not isinstance(name, str) or not name.strip():
            raise ValueError('font-family names must be nonempty strings')
        if name not in result:
            result.append(name)
    return tuple(result)


class FontComboBoxMixin:
    """Populate an ordinary backend ComboBox with validated family names."""
    def __init__(self, model, *, fonts=None, disabled=False):
        super().__init__(text_model=model, disabled=disabled)
        choices = font_choices(self.default_fonts() if fonts is None else fonts)
        with self:
            for name in choices:
                self.font_item(name)
