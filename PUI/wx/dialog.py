from pathlib import Path


def _directory(dir, directory):
    if dir is not None and directory is not None and dir != directory:
        raise ValueError("Use either dir or directory, or matching values")
    return str(directory if directory is not None else dir or "")


def _wildcard(types):
    if not types:
        return wx.FileSelectorDefaultWildcardStr
    parts = types.replace(";;", "|").split("|")
    # Accept both Qt's 'Images (*.png *.jpg)' and wx's 'Images|*.png;*.jpg'.
    if all("(" in part and part.endswith(")") for part in parts):
        pairs = []
        for part in parts:
            label, patterns = part.rsplit("(", 1)
            pairs.extend((part, ";".join(patterns[:-1].split())))
        return "|".join(pairs)
    return "|".join(parts)

from .base import wx

def OpenDirectory(title="Open Directory", dir=None, *, directory=None):
    directory = _directory(dir, directory)
    with wx.DirDialog(None, title, directory, wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dir_dialog:
        if dir_dialog.ShowModal() == wx.ID_CANCEL:
            return None
        return dir_dialog.GetPath()

def OpenFile(title="Open File", dir=None, types=None, *, directory=None):
    directory = _directory(dir, directory)
    types = _wildcard(types)
    with wx.FileDialog(None, title, directory, wildcard=types,
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as file_dialog:
        if file_dialog.ShowModal() == wx.ID_CANCEL:
            return None
        return file_dialog.GetPath()

def OpenFiles(title="Open Files", dir=None, types=None, *, directory=None):
    directory = _directory(dir, directory)
    types = _wildcard(types)
    with wx.FileDialog(None, title, directory, wildcard=types,
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as file_dialog:
        if file_dialog.ShowModal() == wx.ID_CANCEL:
            return None
        return file_dialog.GetPaths()

def SaveFile(default=None, title="Save File", dir=None, types=None, *, directory=None):
    directory = _directory(dir, directory)
    types = _wildcard(types)
    default_file = ""
    if isinstance(default, str):
        path = Path(default)
        default_file = path.name
        if not directory:
            directory = str(path.parent)
    with wx.FileDialog(None, title, directory, default_file, wildcard=types,
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as file_dialog:
        if file_dialog.ShowModal() == wx.ID_CANCEL:
            return None
        return file_dialog.GetPath()

def Information(message="Information", title="Information Dialog"):
    wx.MessageBox(message, title, wx.OK | wx.ICON_INFORMATION)

def Warning(message="Warning", title="Warning Dialog"):
    wx.MessageBox(message, title, wx.OK | wx.ICON_WARNING)

def Critical(message="Critical", title="Critical Dialog"):
    wx.MessageBox(message, title, wx.OK | wx.ICON_ERROR)

def Confirm(message="Confirm", title="Confirm Dialog"):
    dlg = wx.MessageDialog(None, message, title, wx.YES_NO | wx.ICON_QUESTION)
    result = dlg.ShowModal()
    dlg.Destroy()
    return result == wx.ID_YES

def Prompt(prompt="Input", title="Input Dialog", default=""):
    dlg = wx.TextEntryDialog(None, prompt, title, default)
    if dlg.ShowModal() == wx.ID_OK:
        result = dlg.GetValue()
    else:
        result = None
    dlg.Destroy()
    return result
