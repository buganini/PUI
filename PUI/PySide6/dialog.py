from .. import *
from .base import *


def OpenFile(model, title="Open File", dir=None, types=None):
    res = QtWidgets.QFileDialog.getOpenFileName(None, title, dir, types)
    model.value = res[0] or None

def OpenFiles(model, title="Open Files", dir=None, types=None):
    res = QtWidgets.QFileDialog.getOpenFileNames(None, title, dir, types)
    model.value = res[0] or None
