"""Imperative dialogs serviced by Textual's UI loop and serial PUI callbacks."""
from concurrent.futures import Future
from contextvars import ContextVar
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button, Input

callback_app = ContextVar('pui_textual_callback_app', default=None)


class MessageDialog(ModalScreen):
    DEFAULT_CSS = '''
    MessageDialog { align: center middle; }
    MessageDialog > Vertical { width: 60; max-width: 95%; height: auto; max-height: 95%; border: round $primary; padding: 1 2; background: $surface; }
    MessageDialog Static { height: auto; margin-bottom: 1; }
    MessageDialog Input { width: 1fr; }
    MessageDialog Horizontal { height: auto; align-horizontal: right; }
    MessageDialog.warning > Vertical { border: round $warning; }
    MessageDialog.critical > Vertical { border: round $error; }
    '''
    BINDINGS = [('escape', 'cancel', 'Cancel')]

    def __init__(self, kind, message, title, default, future):
        super().__init__(classes=kind)
        self.kind, self.message, self.title_text = kind, message, title
        self.default, self.future = default, future

    def compose(self):
        with Vertical():
            yield Static(self.title_text, markup=False)
            yield Static(self.message, markup=False)
            if self.kind == 'prompt':
                yield Input(value=self.default, id='pui-dialog-input')
            with Horizontal():
                if self.kind in ('confirm', 'prompt'):
                    yield Button('Cancel', id='pui-dialog-cancel')
                yield Button('OK', id='pui-dialog-ok', variant='primary')

    def on_mount(self):
        # Shutdown may remove children while this screen is still mounting.
        if self.future.done() or not self.app.is_running:
            return
        targets = self.query(Input if self.kind == 'prompt' else '#pui-dialog-ok')
        target = next(iter(targets), None)
        if target is not None:
            target.focus()

    def finish(self, value):
        if not self.future.done():
            self.future.set_result(value)
        self.dismiss()

    def action_cancel(self):
        self.finish(False if self.kind == 'confirm' else None)

    def on_button_pressed(self, event):
        event.stop()
        if event.button.id == 'pui-dialog-cancel':
            self.action_cancel()
        else:
            self.finish(True if self.kind == 'confirm' else self.query_one(Input).value if self.kind == 'prompt' else None)

    def on_input_changed(self, event):
        event.stop()

    def on_input_submitted(self, event):
        event.stop()
        self.finish(event.value)

    def on_unmount(self):
        if not self.future.done():
            self.future.set_result(False if self.kind == 'confirm' else None)


def _show_dialog(kind, create_screen):
    app = callback_app.get()
    if app is None:
        raise RuntimeError('Textual dialogs must run in a PUI event callback or get_poster() callback')
    future = Future()
    def show():
        if app._pui_stopping or not app.is_running:
            future.set_result(False if kind == 'confirm' else None)
            return
        for pending in list(app._pui_dialogs):
            if pending.done():
                app._pui_dialogs.pop(pending, None)
        if app._pui_dialogs:
            future.set_exception(RuntimeError('A dialog is already pending'))
            return
        app._pui_dialogs[future] = kind
        future.add_done_callback(lambda _: app._pui_loop.call_soon_threadsafe(app._pui_dialogs.pop, future, None))
        try:
            app.push_screen(create_screen(future))
        except Exception as error:
            future.set_exception(error)
    app._pui_loop.call_soon_threadsafe(show)
    return future.result()


def _dialog(kind, message, title, default=''):
    return _show_dialog(kind, lambda future: MessageDialog(kind, str(message), str(title), str(default), future))


def Information(message='Information', title='Information Dialog'):
    _dialog('information', message, title)


def Warning(message='Warning', title='Warning Dialog'):
    _dialog('warning', message, title)


def Critical(message='Critical', title='Critical Dialog'):
    _dialog('critical', message, title)


def Confirm(message='Confirm', title='Confirm Dialog'):
    return _dialog('confirm', message, title)


def Prompt(prompt='Input', title='Input Dialog', default=''):
    return _dialog('prompt', prompt, title, default)
