from .. import *
from .base import *


def OpenDirectory(model, title="Open Directory", dir=None):
    model.value = None
    res = QtWidgets.QFileDialog.getExistingDirectory(None, title, dir)
    model.value = res

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

def Confirm(model, title="Confirm Dialog", message="Confirm"):
    dlg = QtWidgets.QMessageBox(None)
    dlg.setWindowTitle(title)
    dlg.setText(message)
    dlg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    dlg.setIcon(QtWidgets.QMessageBox.Question)
    button = dlg.exec_()

    if button == QtWidgets.QMessageBox.Yes:
        model.value = True
    else:
        model.value = False

def Prompt(model, title="Input Dialog", prompt="Input"):
    text, ok = QtWidgets.QInputDialog.getText(None, title, prompt, QtWidgets.QLineEdit.Normal, model.value)
    if ok:
        model.value = text
    else:
        model.value = None
