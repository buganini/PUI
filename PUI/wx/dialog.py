from .base import wx

def OpenDirectory(title="Open Directory", directory=""):
    with wx.DirDialog(None, title, directory, wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dir_dialog:
        if dir_dialog.ShowModal() == wx.ID_CANCEL:
            return None
        return dir_dialog.GetPath()

def OpenFile(title="Open File", directory="", types=None):
    if types:
        types = types.replace(";;", "|")
    if types is None:
        types = wx.FileSelectorDefaultWildcardStr
    with wx.FileDialog(None, title, directory, wildcard=types,
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as file_dialog:
        if file_dialog.ShowModal() == wx.ID_CANCEL:
            return None
        return file_dialog.GetPath()

def OpenFiles(title="Open Files", directory="", types=None):
    if types:
        types = types.replace(";;", "|")
    if types is None:
        types = wx.FileSelectorDefaultWildcardStr
    with wx.FileDialog(None, title, directory, wildcard=types,
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as file_dialog:
        if file_dialog.ShowModal() == wx.ID_CANCEL:
            return None
        return file_dialog.GetPaths()

def SaveFile(default, title="Save File", directory="", types=None):
    if types:
        types = types.replace(";;", "|")
    if types is None:
        types = wx.FileSelectorDefaultWildcardStr
    if not directory and isinstance(default, str):
        directory = default
    with wx.FileDialog(None, title, directory, wildcard=types,
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