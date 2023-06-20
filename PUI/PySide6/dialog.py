from .. import *
from .base import *


def SelectFile(model, title="Select File", dir=None, types=None):
    res = QtWidgets.QFileDialog.getOpenFileName(None, title, dir, types)
    model.value = res[0] or None
