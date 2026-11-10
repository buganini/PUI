from .combobox import ComboBox, ComboBoxItem
from ..fontcombobox import FontComboBoxMixin
from ..fontcombobox import DEFAULT_FONTS


class FontComboBox(FontComboBoxMixin, ComboBox):
    font_item = staticmethod(ComboBoxItem)

    @staticmethod
    def default_fonts():
        return DEFAULT_FONTS
