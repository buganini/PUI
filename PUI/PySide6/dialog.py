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

def Information(title="Information Dialog", message="Information"):
    dlg = QtWidgets.QMessageBox(None)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dlg.setIcon(QtWidgets.QMessageBox.Information)
    dlg.exec_()

def Warning(title="Warning Dialog", message="Warning"):
    dlg = QtWidgets.QMessageBox(None)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dlg.setIcon(QtWidgets.QMessageBox.Warning)
    dlg.exec_()

def Critical(title="Critical Dialog", message="Critical"):
    dlg = QtWidgets.QMessageBox(None)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    dlg.setIcon(QtWidgets.QMessageBox.Critical)
    dlg.exec_()

def Confirm(title="Confirm Dialog", message="Confirm"):
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

def Prompt(default, title="Input Dialog", prompt="Input"):
    text, ok = QtWidgets.QInputDialog.getText(None, title, prompt, QtWidgets.QLineEdit.Normal, default)
    if ok:
        return text
    else:
        return None
