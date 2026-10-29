"""Synchronous PUI dialogs backed by Flet's asynchronous UI services."""
import asyncio
from concurrent.futures import Future
from contextvars import ContextVar
from pathlib import Path
import flet as ft
from ..file_filter import flet_extensions
from .._browser.file_selection import initial_directory

callback_app = ContextVar('pui_flet_callback_app', default=None)


def _show(kind, operation):
    app = callback_app.get()
    if app is None:
        raise RuntimeError('Flet dialogs must run in a PUI event callback or get_poster() callback')
    future = Future()

    async def run():
        try:
            value = await operation(app.ui)
            if not future.done():
                future.set_result(value)
        except asyncio.CancelledError:
            if not future.done():
                future.set_result(False if kind == 'confirm' else None)
        except Exception as error:
            if not future.done():
                future.set_exception(error)
        finally:
            app._dialogs.pop(future, None)

    def schedule():
        if app._stopping:
            future.set_result(False if kind == 'confirm' else None)
            return
        app._dialogs[future] = kind
        task = asyncio.create_task(run())
        app._dialog_tasks.add(task)
        task.add_done_callback(app._dialog_tasks.discard)
    app.loop.call_soon_threadsafe(schedule, context=app.context.copy())
    return future.result()


async def _message(page, kind, message, title, default):
    result = asyncio.get_running_loop().create_future()
    cancel = False if kind == 'confirm' else None
    field = ft.TextField(value=str(default), autofocus=True) if kind == 'prompt' else None

    def finish(value):
        if not result.done():
            result.set_result(value)
            dialog.open = False
            page.update()

    def accept(event=None):
        finish(field.value if field is not None else True if kind == 'confirm' else None)

    if field is not None:
        field.on_submit = accept
    actions = []
    if kind in ('confirm', 'prompt'):
        actions.append(ft.TextButton('Cancel', on_click=lambda e: finish(cancel)))
    actions.append(ft.TextButton('OK', on_click=accept))
    icon = {'information': ft.Icons.INFO_OUTLINE, 'warning': ft.Icons.WARNING_AMBER,
            'critical': ft.Icons.ERROR_OUTLINE}.get(kind)
    heading = ft.Text(str(title))
    if icon:
        color = {'information': ft.Colors.BLUE, 'warning': ft.Colors.ORANGE,
                 'critical': ft.Colors.RED}[kind]
        heading = ft.Row([ft.Icon(icon, color=color), heading], tight=True,
                         vertical_alignment=ft.CrossAxisAlignment.CENTER)
    dialog = ft.AlertDialog(
        modal=True, title=heading,
        content=ft.Column([ft.Text(str(message)), field], tight=True) if field is not None else ft.Text(str(message)),
        actions=actions,
        on_dismiss=lambda e: finish(cancel))
    page.show_dialog(dialog)
    try:
        return await result
    finally:
        dialog.open = False
        page.update()


def Information(message='Information', title='Information Dialog'):
    return _show('information', lambda page: _message(page, 'information', message, title, ''))


def Warning(message='Warning', title='Warning Dialog'):
    return _show('warning', lambda page: _message(page, 'warning', message, title, ''))


def Critical(message='Critical', title='Critical Dialog'):
    return _show('critical', lambda page: _message(page, 'critical', message, title, ''))


def Confirm(message='Confirm', title='Confirm Dialog'):
    return _show('confirm', lambda page: _message(page, 'confirm', message, title, ''))


def Prompt(prompt='Input', title='Input Dialog', default=''):
    return _show('prompt', lambda page: _message(page, 'prompt', prompt, title, default))


def _file(mode, title, dir, types, directory, default=None):
    initial = initial_directory(dir, directory)
    name = None
    if default is not None:
        path = Path(str(default)).expanduser()
        name = path.name
        if initial is None and path.parent != Path('.'):
            initial = path.parent
    extensions = flet_extensions(types)

    async def choose(page):
        if page.web or page.platform.is_mobile():
            raise RuntimeError('PUI Flet file dialogs require desktop mode to return filesystem paths')
        picker = ft.FilePicker()
        args = dict(dialog_title=str(title), initial_directory=str(initial) if initial is not None else None)
        if mode == 'directory':
            return await picker.get_directory_path(**args) or None
        args.update(file_type=ft.FilePickerFileType.CUSTOM if extensions else ft.FilePickerFileType.ANY,
                    allowed_extensions=extensions)
        if mode == 'save':
            return await picker.save_file(file_name=name, **args) or None
        files = await picker.pick_files(allow_multiple=mode == 'files', **args)
        if not files:
            return None
        if any(file.path is None for file in files):
            raise RuntimeError('Flet did not return filesystem paths')
        paths = [file.path for file in files]
        return paths if mode == 'files' else paths[0]
    return _show('file', choose)


def OpenDirectory(title='Open Directory', dir=None, *, directory=None):
    return _file('directory', title, dir, None, directory)


def OpenFile(title='Open File', dir=None, types=None, *, directory=None):
    return _file('file', title, dir, types, directory)


def OpenFiles(title='Open Files', dir=None, types=None, *, directory=None):
    return _file('files', title, dir, types, directory)


def SaveFile(default=None, title='Save File', dir=None, types=None, *, directory=None):
    return _file('save', title, dir, types, directory, default)
