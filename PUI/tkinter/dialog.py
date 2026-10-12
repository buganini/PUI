from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog


def _directory(dir, directory):
    if dir is not None and directory is not None and dir != directory:
        raise ValueError('Use either dir or directory, or matching values')
    return str(directory if directory is not None else dir or '')


def _filetypes(types):
    if not types:
        return [('All files', '*')]
    parts = types.replace(';;', '|').split('|')
    if all('(' in part and part.endswith(')') for part in parts):
        pairs = [part.rsplit('(', 1) for part in parts]
        return [(label.strip(), tuple(patterns[:-1].split())) for label, patterns in pairs]
    if len(parts) % 2:
        raise ValueError('File filters require label/pattern pairs')
    return [(parts[i], tuple(parts[i+1].replace(';', ' ').split())) for i in range(0, len(parts), 2)]


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
