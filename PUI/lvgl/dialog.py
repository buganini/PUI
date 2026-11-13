"""Blocking dialogs: they run a nested LVGL loop until the user answers.

Application callbacks are dispatched from the runtime queue (outside
lv_timer_handler), so a dialog opened from a click handler can process input.
"""
from __future__ import annotations
import fnmatch
import os
import time
from pathlib import Path
from ..file_filter import patterns
from .base import *
from .overlay import create_dialog, Handlers

# Built-in LVGL symbols (Font Awesome subset bundled with Montserrat).
_ICONS = {'information': (b'\xef\x83\xb3', 0x2196F3), 'warning': (b'\xef\x81\xb1', 0xF9A825),
          'critical': (b'\xef\x80\x8d', 0xD32F2F), 'question': (b'?', 0x2196F3)}
_SYMBOL_DIRECTORY = b'\xef\x81\xbb'
_SYMBOL_FILE = b'\xef\x85\x9b'
_SYMBOL_UP = b'\xef\x81\xb7'


class _Dialog:
    def __init__(self, title, width=None, height=None):
        if runtime.native_depth:
            raise RuntimeError('LVGL dialogs cannot be opened from inside a native LVGL callback')
        self.app = getattr(runtime, 'app', None)
        if self.app is None or self.app.ui is None:
            raise RuntimeError('LVGL dialogs require a running Application')
        self.handlers = Handlers()
        self.done = False
        self.value = None
        self.backdrop, self.panel, self.body, close = create_dialog(title, width, height, on_close=True)
        self.on(close, lib.LV_EVENT_CLICKED, lambda: self.finish(None))

    def on(self, obj, code, callback):
        self.handlers.on(obj, code, lambda c, e: runtime.post(callback))

    def finish(self, value):
        self.value = value
        self.done = True

    def row(self, parent=None, end=False):
        row = lib.lv_obj_create(self.body if parent is None else parent)
        lib.lv_obj_remove_style_all(row)
        # Content width, at least the body's: a plain 100% would depend on
        # the content-sized dialog body and collapse.
        lib.lv_obj_set_size(row, lib.LV_SIZE_CONTENT, lib.LV_SIZE_CONTENT)
        lib.lv_obj_set_style_min_width(row, lib.lv_pct(100), SEL)
        lib.lv_obj_set_flex_flow(row, lib.LV_FLEX_FLOW_ROW)
        lib.lv_obj_set_flex_align(row, lib.LV_FLEX_ALIGN_END if end else lib.LV_FLEX_ALIGN_START,
                                  lib.LV_FLEX_ALIGN_CENTER, lib.LV_FLEX_ALIGN_CENTER)
        lib.lv_obj_set_style_pad_column(row, 8, SEL)
        return row

    def label(self, parent, text, color=None):
        label = lib.lv_label_create(parent)
        lib.lv_label_set_text(label, text_bytes(text) if isinstance(text, str) else text)
        if color is not None:
            lib.lv_obj_set_style_text_color(label, lib.lv_color_hex(color), SEL)
        return label

    def button(self, parent, caption, callback):
        button = lib.lv_button_create(parent)
        self.label(button, caption)
        self.on(button, lib.LV_EVENT_CLICKED, callback)
        return button

    def run(self):
        try:
            while not self.done and lib.pui_lvgl_is_running():
                wait = self.app.process_events()
                if not self.done and wait > 0:
                    time.sleep(min(wait, 0.01))
        finally:
            self.handlers.clear()
            if lib.pui_lvgl_is_running():
                lib.lv_obj_delete(self.backdrop)
        return self.value


def _message(kind, message, title, buttons):
    dialog = _Dialog(title)
    row = dialog.row()
    lib.lv_obj_set_style_pad_column(row, 12, SEL)
    symbol, color = _ICONS[kind]
    dialog.label(row, symbol, color)
    text = dialog.label(row, str(message))
    lib.lv_obj_set_style_max_width(text, 480, SEL)
    lib.lv_label_set_long_mode(text, lib.LV_LABEL_LONG_MODE_WRAP)
    actions = dialog.row(end=True)
    for caption, value in buttons:
        dialog.button(actions, caption, lambda value=value: dialog.finish(value))
    return dialog.run()


def Information(message="Information", title="Information Dialog"):
    _message('information', message, title, (('OK', None),))


def Warning(message="Warning", title="Warning Dialog"):
    _message('warning', message, title, (('OK', None),))


def Critical(message="Critical", title="Critical Dialog"):
    _message('critical', message, title, (('OK', None),))


def Confirm(message="Confirm", title="Confirm Dialog"):
    return bool(_message('question', message, title, (('No', False), ('Yes', True))))


def Prompt(prompt="Input", title="Input Dialog", default=""):
    dialog = _Dialog(title)
    dialog.label(dialog.body, str(prompt))
    field = lib.lv_textarea_create(dialog.body)
    lib.lv_textarea_set_one_line(field, True)
    lib.lv_obj_set_width(field, 320)
    lib.lv_textarea_set_text(field, text_bytes('' if default is None else default))
    lib.lv_group_focus_obj(field)

    def accept():
        raw = lib.lv_textarea_get_text(field)
        dialog.finish(ffi.string(raw).decode('utf-8', 'replace') if raw != ffi.NULL else '')
    dialog.on(field, lib.LV_EVENT_READY, accept)
    actions = dialog.row(end=True)
    dialog.button(actions, 'Cancel', lambda: dialog.finish(None))
    dialog.button(actions, 'OK', accept)
    return dialog.run()


# ---------------------------------------------------------------------------
# File browser
# ---------------------------------------------------------------------------

def _directory(dir, directory):
    if dir is not None and directory is not None and dir != directory:
        raise ValueError('Use either dir or directory, or matching values')
    value = directory if directory is not None else dir
    path = Path(value).expanduser() if value else Path.cwd()
    while not path.is_dir() and path != path.parent:
        path = path.parent
    return path.resolve()


class _FileDialog(_Dialog):
    def __init__(self, title, start, *, mode, types=None, filename=''):
        super().__init__(title, width=560, height=440)
        self.mode = mode  # 'file', 'files', 'directory', 'save'
        self.patterns = [p for p in patterns(types) if p != '*'] if types else []
        self.cwd = start
        self.selected = []
        bar = self.row()
        self.button(bar, _SYMBOL_UP, self.up)
        self.path_label = self.label(bar, '')
        lib.lv_obj_set_flex_grow(self.path_label, 1)
        lib.lv_label_set_long_mode(self.path_label, lib.LV_LABEL_LONG_MODE_CLIP)
        self.list = lib.lv_obj_create(self.body)
        lib.lv_obj_set_width(self.list, lib.lv_pct(100))
        lib.lv_obj_set_flex_grow(self.list, 1)
        lib.lv_obj_set_flex_flow(self.list, lib.LV_FLEX_FLOW_COLUMN)
        lib.lv_obj_set_style_pad_all(self.list, 2, SEL)
        lib.lv_obj_set_style_pad_row(self.list, 0, SEL)
        lib.lv_obj_set_style_radius(self.list, 0, SEL)
        lib.lv_obj_set_scroll_dir(self.list, lib.LV_DIR_VER)
        lib.lv_obj_set_style_max_height(self.body, lib.lv_pct(100), SEL)
        self.name_field = None
        if mode == 'save':
            row = self.row()
            self.label(row, 'Name')
            self.name_field = lib.lv_textarea_create(row)
            lib.lv_textarea_set_one_line(self.name_field, True)
            lib.lv_obj_set_flex_grow(self.name_field, 1)
            lib.lv_textarea_set_text(self.name_field, text_bytes(filename))
            self.on(self.name_field, lib.LV_EVENT_READY, self.accept)
        if self.patterns:
            self.label(self.body, 'Showing: ' + ' '.join(self.patterns), 0x707070)
        actions = self.row(end=True)
        self.button(actions, 'Cancel', lambda: self.finish(None))
        caption = {'directory': 'Select', 'save': 'Save'}.get(mode, 'Open')
        self.button(actions, caption, self.accept)
        self.rows = []
        self.refresh()

    def up(self):
        if self.cwd.parent != self.cwd:
            self.cwd = self.cwd.parent
            self.selected = []
            self.refresh()

    def entries(self):
        try:
            names = sorted(os.listdir(self.cwd), key=str.lower)
        except OSError:
            names = []
        directories, files = [], []
        for name in names:
            if name.startswith('.'):
                continue
            path = self.cwd / name
            if path.is_dir():
                directories.append(path)
            elif self.mode != 'directory' and (not self.patterns or any(
                    fnmatch.fnmatch(name.lower(), p.lower()) for p in self.patterns)):
                files.append(path)
        return directories, files

    def refresh(self):
        lib.lv_label_set_text(self.path_label, text_bytes(str(self.cwd)))
        lib.lv_obj_clean(self.list)
        self.rows = []
        directories, files = self.entries()
        for path in directories + files:
            row = lib.lv_obj_create(self.list)
            lib.lv_obj_remove_style_all(row)
            lib.lv_obj_set_size(row, lib.lv_pct(100), lib.LV_SIZE_CONTENT)
            lib.lv_obj_set_flex_flow(row, lib.LV_FLEX_FLOW_ROW)
            lib.lv_obj_set_style_pad_all(row, 4, SEL)
            lib.lv_obj_set_style_pad_column(row, 8, SEL)
            lib.lv_obj_set_style_bg_color(row, lib.lv_color_hex(0x2196F3), lib.LV_STATE_CHECKED)
            lib.lv_obj_set_style_bg_opa(row, lib.LV_OPA_COVER, lib.LV_STATE_CHECKED)
            lib.lv_obj_set_style_text_color(row, lib.lv_color_hex(0xFFFFFF), lib.LV_STATE_CHECKED)
            lib.lv_obj_add_flag(row, lib.LV_OBJ_FLAG_CLICKABLE)
            self.label(row, _SYMBOL_DIRECTORY if path.is_dir() else _SYMBOL_FILE)
            self.label(row, path.name)
            self.on(row, lib.LV_EVENT_CLICKED, lambda path=path: self.click(path))
            self.on(row, lib.LV_EVENT_DOUBLE_CLICKED, lambda path=path: self.double(path))
            self.rows.append((row, path))
        self.show_selection()

    def show_selection(self):
        for row, path in self.rows:
            lib.lv_obj_set_state(row, lib.LV_STATE_CHECKED, path in self.selected)

    def click(self, path):
        if path.is_dir():
            self.selected = [path] if self.mode == 'directory' else []
        elif self.mode == 'files':
            self.selected = [p for p in self.selected if p != path] if path in self.selected else self.selected + [path]
        else:
            self.selected = [path]
            if self.name_field is not None:
                lib.lv_textarea_set_text(self.name_field, text_bytes(path.name))
        self.show_selection()

    def double(self, path):
        if path.is_dir():
            self.cwd = path
            self.selected = []
            self.refresh()
        else:
            self.selected = [path]
            self.accept()

    def accept(self):
        if self.mode == 'directory':
            chosen = self.selected[0] if self.selected else self.cwd
            self.finish(str(chosen))
        elif self.mode == 'save':
            raw = lib.lv_textarea_get_text(self.name_field)
            name = ffi.string(raw).decode('utf-8', 'replace').strip() if raw != ffi.NULL else ''
            if name:
                self.finish(str(self.cwd / name))
        elif self.mode == 'files':
            files = [str(p) for p in self.selected if p.is_file()]
            if files:
                self.finish(files)
        else:
            files = [p for p in self.selected if p.is_file()]
            if files:
                self.finish(str(files[0]))


def OpenDirectory(title="Open Directory", dir=None, *, directory=None):
    return _FileDialog(title, _directory(dir, directory), mode='directory').run()


def OpenFile(title="Open File", dir=None, types=None, *, directory=None):
    return _FileDialog(title, _directory(dir, directory), mode='file', types=types).run()


def OpenFiles(title="Open Files", dir=None, types=None, *, directory=None):
    return _FileDialog(title, _directory(dir, directory), mode='files', types=types).run()


def SaveFile(default=None, title="Save File", dir=None, types=None, *, directory=None):
    filename = ''
    if default is not None and directory is None and not dir:
        path = Path(str(default)).expanduser()
        filename = path.name
        dir = str(path.parent)
    elif default is not None:
        filename = Path(str(default)).name
    return _FileDialog(title, _directory(dir, directory), mode='save', types=types, filename=filename).run()
