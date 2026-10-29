from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog


def _directory(dir, directory):
    if dir is not None and directory is not None and dir != directory:
        raise ValueError('Use either dir or directory, or matching values')
    return str(directory if directory is not None else dir or '')


from ..file_filter import tk_filter as _filetypes


def OpenDirectory(title='Open Directory', dir=None, *, directory=None):
    return filedialog.askdirectory(title=title, initialdir=_directory(dir, directory), mustexist=True) or None


def OpenFile(title='Open File', dir=None, types=None, *, directory=None):
    return filedialog.askopenfilename(title=title, initialdir=_directory(dir, directory), filetypes=_filetypes(types)) or None


def OpenFiles(title='Open Files', dir=None, types=None, *, directory=None):
    paths = filedialog.askopenfilenames(title=title, initialdir=_directory(dir, directory), filetypes=_filetypes(types))
    return list(paths) if paths else None


def SaveFile(default=None, title='Save File', dir=None, types=None, *, directory=None):
    initialdir = _directory(dir, directory)
    initialfile = ''
    if default is not None:
        path = Path(default)
        initialfile = path.name
        if not initialdir:
            initialdir = str(path.parent)
    return filedialog.asksaveasfilename(title=title, initialdir=initialdir, initialfile=initialfile,
                                      filetypes=_filetypes(types), confirmoverwrite=True) or None


def Information(message='Information', title='Information Dialog'):
    messagebox.showinfo(title, message)


def Warning(message='Warning', title='Warning Dialog'):
    messagebox.showwarning(title, message)


def Critical(message='Critical', title='Critical Dialog'):
    messagebox.showerror(title, message)


def Confirm(message='Confirm', title='Confirm Dialog'):
    return messagebox.askyesno(title, message)


def Prompt(prompt='Input', title='Input Dialog', default=''):
    return simpledialog.askstring(title, prompt, initialvalue=default)
