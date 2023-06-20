from .. import *
from .base import *


def OpenFile(model, title="Open File", dir=None, types=None):
    model.value = None
    res = QtWidgets.QFileDialog.getOpenFileName(None, title, dir, types)
    model.value = res[0] or None

def OpenFiles(model, title="Open Files", dir=None, types=None):
    model.value = None
    res = QtWidgets.QFileDialog.getOpenFileNames(None, title, dir, types)
    model.value = res[0] or None

def SaveFile(model, title="Save File", dir=None, types=None):
    if not dir:
        value = model.value
        if isinstance(value, str):
            dir = value
    res = QtWidgets.QFileDialog.getSaveFileName(None, title, dir, types)
    model.value = res[0] or None
