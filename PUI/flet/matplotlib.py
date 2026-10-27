"""Shared Matplotlib drawing with Flet's native gesture and keyboard controls."""
from types import SimpleNamespace
from .base import ft, FView
from .canvas import Canvas
from .._matplotlib import MatplotlibMixin


class MatplotlibCanvas(MatplotlibMixin, Canvas):
    def __init__(self, plotter, *args, **kwargs):
        super().__init__(plotter, *args, **kwargs)
        self.keyboard = None
        self._held_keys = set()

    def update(self, prev):
        if prev is not None:
            self.keyboard, self._held_keys = prev.keyboard, prev._held_keys
        super().update(prev)
        if self.keyboard is None:
            self.keyboard = ft.KeyboardListener(content=self.gesture)
        self.keyboard.content = self.gesture
        self.keyboard.expand = self.gesture.expand
        self.keyboard.on_key_down = self.on_mpl_key_down
        self.keyboard.on_key_repeat = self.on_mpl_key_down
        self.keyboard.on_key_up = self.on_mpl_key_up
        self.shell.content = self.keyboard

    def _modifiers(self):
        flags = {'Shift': 1, 'Control': 2, 'Alt': 4, 'Meta': 8}
        return sum(flag for key, flag in flags.items()
                   if any(held == key or held.startswith(key + ' ') for held in self._held_keys))

    def _key_event(self, raw):
        # Flutter sends logicalKey.keyLabel, including side-specific modifiers
        # and uppercase Latin letters independent of the Shift state.
        key = raw
        for modifier in ('Shift', 'Control', 'Alt', 'Meta'):
            if key.startswith(modifier + ' '):
                key = modifier
        key = {'Arrow Left': 'ArrowLeft', 'Arrow Right': 'ArrowRight',
               'Arrow Up': 'ArrowUp', 'Arrow Down': 'ArrowDown',
               'Page Up': 'PageUp', 'Page Down': 'PageDown'}.get(key, key)
        if len(key) == 1 and not self._modifiers() & 1:
            key = key.lower()
        return SimpleNamespace(key=key, code=raw, modifiers=self._modifiers())

    async def on_mpl_key_down(self, event):
        node = self.get_node()
        if node.destroyed:
            return
        node._held_keys.add(event.key)
        node._mpl_keydown(node._key_event(event.key))

    async def on_mpl_key_up(self, event):
        node = self.get_node()
        if node.destroyed:
            return
        node._held_keys.discard(event.key)
        node._mpl_keyup(node._key_event(event.key))

    async def on_down(self, event, *args, **kwargs):
        node = self.get_node()
        app = FView.application(node)
        if not node.destroyed and app is not None and app.ready:
            await node.keyboard.focus()
        await super().on_down(event, *args, **kwargs)

    def dispatch_pointer(self, position, callback, button=0, **fields):
        node = self.get_node()
        if node.destroyed:
            return
        fields['modifiers'] = node._modifiers()
        # KeyboardListener exposes no blur callback. Clear held keys when the
        # pointer leaves; modifier presses made outside this control are unknown.
        if callback == '_onMouseLeave' and node.figure_canvas is not None:
            events = node.figure_canvas.input_events
            for raw in tuple(events.keys):
                node._mpl_keyup(SimpleNamespace(key=raw, modifiers=0))
            node._held_keys.clear()
        super().dispatch_pointer(position, callback, button, **fields)

    def releaseRetiredRefs(self):
        self.keyboard = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        if self.keyboard is not None:
            self.keyboard.on_key_down = self.keyboard.on_key_up = self.keyboard.on_key_repeat = None
        self.keyboard = None
        self._held_keys.clear()
        super().destroy(direct)
