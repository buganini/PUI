from .combobox import ComboBox, ComboBoxItem
from ..fontcombobox import FontComboBoxMixin
import wx


class FontComboBox(FontComboBoxMixin, ComboBox):
    font_item = staticmethod(ComboBoxItem)

    @staticmethod
    def default_fonts():
        return wx.FontEnumerator.GetFacenames()
