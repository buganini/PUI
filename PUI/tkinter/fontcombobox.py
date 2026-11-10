from .combobox import ComboBox, ComboBoxItem
from ..fontcombobox import FontComboBoxMixin
from tkinter import font


class FontComboBox(FontComboBoxMixin, ComboBox):
    font_item = staticmethod(ComboBoxItem)

    @staticmethod
    def default_fonts():
        return font.families()
