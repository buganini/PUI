from PySide6 import QtCore, QtWidgets
from .base import QtBaseWidget
from ..fontcombobox import font_choices
from .. import PUIEvent


class FontComboBox(QtBaseWidget):
    def __init__(self, model, *, fonts=None, disabled=False):
        self._internal_tag = str(fonts is None)
        super().__init__()
        self.model = model
        self.fonts = None if fonts is None else font_choices(fonts)
        self.disabled = disabled

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QFontComboBox() if self.fonts is None else QtWidgets.QComboBox()
            self.ui.setEditable(False)
            self.ui.activated.connect(lambda index: self.get_node().choose(index))
        super().update(prev)
        with QtCore.QSignalBlocker(self.ui):
            if self.fonts is not None:
                if tuple(self.ui.itemText(i) for i in range(self.ui.count())) != self.fonts:
                    self.ui.clear()
                    self.ui.addItems(self.fonts)
            self.ui.setCurrentIndex(self.ui.findText(str(self.model.value)))
        self.ui.setEnabled(not self.disabled)

    def choose(self, index):
        if not self.disabled and 0 <= index < self.ui.count():
            self.model.value = self.ui.itemText(index)
            event = PUIEvent()
            event.value = index
            self._change(event)
