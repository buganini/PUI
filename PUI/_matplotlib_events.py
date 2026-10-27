"""Translate logical PUI Canvas input into Matplotlib backend events."""
from matplotlib.backend_bases import KeyEvent, LocationEvent, MouseButton, MouseEvent


BUTTONS = {1: MouseButton.LEFT, 2: MouseButton.RIGHT, 4: MouseButton.MIDDLE,
           8: MouseButton.BACK, 16: MouseButton.FORWARD}
MODIFIERS = ((1, 'shift'), (2, 'ctrl'), (4, 'alt'), (8, 'super'))
KEYS = {'Control': 'control', 'Shift': 'shift', 'Alt': 'alt', 'Meta': 'super',
        'Enter': 'enter', 'Escape': 'escape', ' ': ' ', 'Space': ' ',
        'ArrowLeft': 'left', 'ArrowRight': 'right', 'ArrowUp': 'up', 'ArrowDown': 'down',
        'Backspace': 'backspace', 'Delete': 'delete', 'Tab': 'tab',
        'PageUp': 'pageup', 'PageDown': 'pagedown', 'Home': 'home', 'End': 'end'}


def key_name(key, modifiers=0):
    key = KEYS.get(key, key.lower() if len(key) > 1 else key)
    parts = [name for flag, name in MODIFIERS if modifiers & flag]
    own = 'ctrl' if key == 'control' else key
    if own in parts:
        parts.remove(own)
    # Browser text keys already encode Shift in the resulting character.
    if len(key) == 1 and key.isupper() and 'shift' in parts:
        parts.remove('shift')
    return '+'.join([*parts, key])


class MatplotlibEvents:
    def __init__(self, canvas):
        self.canvas = canvas
        self.position = (None, None)
        self.buttons = set()
        self.keys = {}

    def pointer(self, name, event):
        canvas = self.canvas
        # RendererPUI uses logical pixels, regardless of backing-store DPR.
        x, y = event.x, canvas.figure.bbox.height - event.y
        self.position = x, y
        modifiers = getattr(event, 'modifiers', None) or 0
        mods = [label for flag, label in MODIFIERS if modifiers & flag]
        if name in ('figure_enter_event', 'figure_leave_event'):
            LocationEvent(name, canvas, x, y, guiEvent=event, modifiers=mods)._process()
            return
        button = BUTTONS.get(getattr(event, 'button', 0))
        if name == 'button_press_event' and button:
            self.buttons.add(button)
        elif name == 'button_release_event':
            # A lost pointer capture can report no changed button. Release all
            # held buttons so a navigation controller cannot remain dragging.
            if getattr(event, 'cancelled', False):
                for held in tuple(self.buttons):
                    self.buttons.discard(held)
                    MouseEvent(name, canvas, x, y, held, guiEvent=event, modifiers=mods)._process()
                return
            self.buttons.discard(button)
        kwargs = {}
        if name == 'motion_notify_event':
            mask = getattr(event, 'buttons', None)
            if mask is not None:
                self.buttons = {value for flag, value in BUTTONS.items() if mask & flag}
            kwargs['buttons'] = self.buttons.copy()
            if button is None and len(self.buttons) == 1:
                button = next(iter(self.buttons))
        if name == 'scroll_event':
            if hasattr(event, 'delta_y'):
                # DOM lines/pages have no universal pixel size. One line is one
                # step; a page is one step; 100 CSS pixels form one smooth step.
                delta = event.delta_y
                step = -delta / 100 if event.delta_mode == 'pixel' else -delta
            else:
                step = (getattr(event, 'v_delta', 0) or 0) / 120
                if not step:
                    step = (getattr(event, 'y_delta', 0) or 0) / 100
            if not step:
                return  # Matplotlib scroll_event has a single vertical axis.
            kwargs['step'] = step
        MouseEvent(name, canvas, x, y, button,
                   key=next(reversed(self.keys.values()), None),
                   dblclick=getattr(event, 'dblclick', False), guiEvent=event,
                   modifiers=mods, **kwargs)._process()

    def key(self, name, event):
        raw = getattr(event, 'code', None) or event.key
        key = key_name(event.key, getattr(event, 'modifiers', 0) or 0)
        if name == 'key_press_event':
            self.keys[raw] = key
        else:
            key = self.keys.pop(raw, key)
        KeyEvent(name, self.canvas, key, *self.position, guiEvent=event)._process()

    def reset(self):
        x, y = self.position
        for button in tuple(self.buttons):
            self.buttons.discard(button)
            MouseEvent('button_release_event', self.canvas, x, y, button)._process()
        for key in tuple(self.keys.values()):
            KeyEvent('key_release_event', self.canvas, key, x, y)._process()
        self.keys.clear()
