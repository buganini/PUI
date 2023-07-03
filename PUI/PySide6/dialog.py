from .. import *
from .base import *


def OpenDirectory(title="Open Directory", dir=None):
    res = QtWidgets.QFileDialog.getExistingDirectory(None, title, dir)
    return res

def OpenFile(title="Open File", dir=None, types=None):
    res = QtWidgets.QFileDialog.getOpenFileName(None, title, dir, types)
    return res[0] or None

def OpenFiles(title="Open Files", dir=None, types=None):
    res = QtWidgets.QFileDialog.getOpenFileNames(None, title, dir, types)
    return res[0] or None

def SaveFile(default, title="Save File", dir=None, types=None):
    if not dir:
        value = default
        if isinstance(value, str):
            dir = value
    res = QtWidgets.QFileDialog.getSaveFileName(None, title, dir, types)
    return res[0] or None

def Information(message="Information", title="Information Dialog"):
    dlg = QtWidgets.QMessageBox(None)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dlg.setIcon(QtWidgets.QMessageBox.Information)
    dlg.exec_()

def Warning(message="Warning", title="Warning Dialog"):
    dlg = QtWidgets.QMessageBox(None)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dlg.setIcon(QtWidgets.QMessageBox.Warning)
    dlg.exec_()

def Critical(message="Critical", title="Critical Dialog"):
    dlg = QtWidgets.QMessageBox(None)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dlg.setIcon(QtWidgets.QMessageBox.Critical)
    dlg.exec_()

def Confirm(message="Confirm", title="Confirm Dialog"):
    dlg = QtWidgets.QMessageBox(None)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    dlg.setIcon(QtWidgets.QMessageBox.Question)
    button = dlg.exec_()

    if button == QtWidgets.QMessageBox.Yes:
        return True
    else:
        return False

def Prompt(prompt="Input", title="Input Dialog", default=""):
    text, ok = QtWidgets.QInputDialog.getText(None, title, prompt, QtWidgets.QLineEdit.Normal, default)
    if ok:
        return text
    else:
        return None
