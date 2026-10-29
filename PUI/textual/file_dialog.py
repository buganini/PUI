"""Terminal file selection; paths refer to the machine running the application."""
import asyncio
from pathlib import Path

from rich.text import Text
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, OptionList, SelectionList, Static
from textual.widgets.option_list import Option

from .._browser.file_selection import filters, initial_directory, matches
from .dialog import _show_dialog


def _listing(value, base, patterns, directories_only):
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise ValueError('Choose an existing directory.')
    entries = []
    for item in path.iterdir():
        try:
            directory = item.is_dir()
            if not directory and (directories_only or not item.is_file() or not matches(item.name, patterns)):
                continue
            entries.append((item, directory))
        except OSError:
            continue
    entries.sort(key=lambda item: (not item[1], item[0].name.casefold()))
    return path, entries


def _validate(mode, directory, names, patterns):
    paths = []
    for name in names:
        path = Path(name).expanduser()
        if not path.is_absolute():
            path = directory / path
        path = path.resolve()
        if mode == 'directory':
            if not path.is_dir():
                raise ValueError('Choose an existing directory.')
        elif mode == 'save':
            if not path.parent.is_dir() or (path.exists() and not path.is_file()):
                raise ValueError('Choose a file in an existing directory.')
        elif not path.is_file() or not matches(path.name, patterns):
            raise ValueError('Choose an existing file matching the filter.')
        paths.append(str(path))
    if not paths:
        raise ValueError('Select at least one file.')
    return paths, mode == 'save' and Path(paths[0]).exists()


class FileDialog(ModalScreen):
    DEFAULT_CSS = '''
    FileDialog { align: center middle; }
    FileDialog > Vertical { width: 76; max-width: 95%; height: 30; max-height: 95%; border: round $primary; padding: 0 1; background: $surface; overflow-y: auto; }
    FileDialog #file-title { height: 1; margin: 1 0; }
    FileDialog Horizontal { height: 3; }
    FileDialog Button { min-width: 6; width: auto; height: 3; margin: 0; }
    FileDialog #file-path { width: 1fr; margin: 0 1; }
    FileDialog OptionList { height: 1fr; min-height: 3; }
    FileDialog #file-name { height: 3; }
    FileDialog #file-status { height: auto; max-height: 3; }
    FileDialog #file-summary { width: 1fr; height: 1; margin-top: 1; }
    FileDialog #file-confirm { margin-left: 1; }
    '''
    BINDINGS = [('escape', 'cancel', 'Cancel')]

    def __init__(self, mode, title, initial, patterns, default, future):
        super().__init__()
        self.mode, self.title_text, self.initial = mode, title, initial
        self.patterns, self.default, self.future = patterns, default, future
        self.directory = Path.cwd()
        self.entries = []
        self.selected = []
        self.generation = 0
        self.busy = False
        self.overwrite = None

    def compose(self):
        with Vertical():
            yield Static(self.title_text, id='file-title', markup=False)
            with Horizontal():
                yield Button('Up', id='file-up')
                yield Input(str(self.initial), id='file-path')
                yield Button('Go', id='file-go')
            if self.mode == 'files':
                yield SelectionList(id='file-entries')
            else:
                yield OptionList(id='file-entries')
            if self.patterns:
                yield Static(', '.join(self.patterns), markup=False)
            if self.mode == 'save':
                yield Static('File name', markup=False)
                yield Input(self.default, id='file-name')
            yield Static('', id='file-status', markup=False)
            with Horizontal():
                yield Static('', id='file-summary', markup=False)
                yield Button('Cancel', id='file-cancel')
                yield Button('Save' if self.mode == 'save' else 'Open this folder' if self.mode == 'directory' else 'Open', id='file-confirm', variant='primary')

    def on_mount(self):
        if not self.future.done() and self.app.is_running:
            self.navigate(str(self.initial))

    def status(self, message):
        self.query_one('#file-status', Static).update(message)

    def update_controls(self):
        self.query_one('#file-entries').disabled = self.busy
        if self.mode == 'save':
            self.query_one('#file-name', Input).disabled = self.busy
        self.query_one('#file-up', Button).disabled = self.busy or self.directory == self.directory.parent
        self.query_one('#file-confirm', Button).disabled = self.busy or (self.mode in ('file', 'files') and not self.selected)
        self.query_one('#file-summary', Static).update(f'{len(self.selected)} files selected' if self.mode == 'files' else '')

    def navigate(self, value):
        self.generation += 1
        generation = self.generation
        self.busy = True
        self.overwrite = None
        if self.mode == 'save':
            self.query_one('#file-confirm', Button).label = 'Save'
        self.status('Loading…')
        self.update_controls()
        self.run_worker(self.load(value, generation), group='file-io', exclusive=True)

    async def load(self, value, generation):
        try:
            # This pool is separate from the single callback executor blocked on
            # the dialog result. Never queue filesystem work onto that executor.
            path, entries = await asyncio.to_thread(_listing, value, self.directory, self.patterns, self.mode == 'directory')
            if self.future.done() or generation != self.generation:
                return
            self.directory, self.entries, self.selected = path, entries, []
            self.query_one('#file-path', Input).value = str(path)
            rows = self.query_one('#file-entries', OptionList)
            rows.clear_options()
            if self.mode == 'files':
                rows.add_options([(Text(('▸ ' if is_dir else '  ') + item.name), str(item), False) for item, is_dir in entries])
            else:
                rows.add_options([Option(Text(('▸ ' if is_dir else '  ') + item.name), id=str(item)) for item, is_dir in entries])
            self.status('' if entries else 'No subfolders' if self.mode == 'directory' else 'No files')
        except (OSError, ValueError, RuntimeError) as error:
            if not self.future.done() and generation == self.generation:
                self.query_one('#file-path', Input).value = str(self.directory)
                self.status(str(error))
        finally:
            if not self.future.done() and generation == self.generation:
                self.busy = False
                self.update_controls()

    def on_option_list_option_selected(self, event):
        event.stop()
        if self.mode == 'files' or self.busy:
            return
        entry = next((entry for entry in self.entries if str(entry[0]) == event.option_id), None)
        if entry is None:
            return
        item, directory = entry
        if directory:
            self.navigate(str(item))
        elif self.mode == 'save':
            self.query_one('#file-name', Input).value = item.name
        else:
            self.selected = [str(item)]
            self.update_controls()

    def on_selection_list_selection_toggled(self, event):
        event.stop()
        if self.busy:
            return
        entry = next((entry for entry in self.entries if str(entry[0]) == event.selection.value), None)
        if entry is None:
            return
        item, directory = entry
        if directory:
            event.selection_list.deselect(str(item))
            self.navigate(str(item))
        else:
            self.selected = list(event.selection_list.selected)
            self.update_controls()

    def on_input_changed(self, event):
        event.stop()
        self.overwrite = None
        if self.mode == 'save':
            self.query_one('#file-confirm', Button).label = 'Save'

    def on_input_submitted(self, event):
        event.stop()
        if event.input.id == 'file-path':
            self.navigate(event.value)
        else:
            self.confirm()

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == 'file-cancel':
            self.action_cancel()
        elif event.button.id == 'file-up':
            self.navigate(str(self.directory.parent))
        elif event.button.id == 'file-go':
            self.navigate(self.query_one('#file-path', Input).value)
        elif event.button.id == 'file-confirm':
            self.confirm()

    def confirm(self):
        if self.busy:
            return
        if self.mode == 'save':
            name = self.query_one('#file-name', Input).value
            if not name.strip():
                self.status('Enter a file name.')
                return
            names = [name]
        else:
            names = [str(self.directory)] if self.mode == 'directory' else self.selected[:]
        self.busy = True
        self.update_controls()
        self.run_worker(self.validate(names, self.generation), group='file-io', exclusive=True)

    async def validate(self, names, generation):
        try:
            paths, exists = await asyncio.to_thread(_validate, self.mode, self.directory, names, self.patterns)
            if self.future.done() or generation != self.generation:
                return
            if exists and self.overwrite != paths[0]:
                self.overwrite = paths[0]
                self.status(f'Replace the existing file? {paths[0]}')
                self.query_one('#file-confirm', Button).label = 'Replace'
            else:
                self.finish(paths if self.mode == 'files' else paths[0])
        except (OSError, ValueError, RuntimeError) as error:
            if not self.future.done() and generation == self.generation:
                self.status(str(error))
        finally:
            if not self.future.done() and generation == self.generation:
                self.busy = False
                self.update_controls()

    def finish(self, value):
        if not self.future.done():
            self.future.set_result(value)
            self.dismiss()

    def action_cancel(self):
        self.finish(None)

    def on_unmount(self):
        if not self.future.done():
            self.future.set_result(None)


def _choose(mode, title, dir, types, directory, default=None):
    initial = initial_directory(dir, directory)
    name = ''
    if default is not None:
        path = Path(str(default)).expanduser()
        name = path.name
        if initial is None and path.parent != Path('.'):
            initial = path.parent
    initial = initial if initial is not None else Path.cwd()
    patterns = filters(types)
    return _show_dialog('file', lambda future: FileDialog(mode, str(title), initial, patterns, name, future))


def OpenDirectory(title='Open Directory', dir=None, *, directory=None):
    return _choose('directory', title, dir, None, directory)


def OpenFile(title='Open File', dir=None, types=None, *, directory=None):
    return _choose('file', title, dir, types, directory)


def OpenFiles(title='Open Files', dir=None, types=None, *, directory=None):
    return _choose('files', title, dir, types, directory)


def SaveFile(default=None, title='Save File', dir=None, types=None, *, directory=None):
    return _choose('save', title, dir, types, directory, default)
