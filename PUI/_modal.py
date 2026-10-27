"""State-driven lifecycle shared by non-blocking declarative modal hosts."""


class ModalMixin:
    pui_terminal = False
    pui_outoforder = True
    pui_detached = True

    def __init__(self, status, offValue=None, title=None, size=None,
                 maximize=None, fullscreen=None):
        super().__init__()
        self.status, self.offValue = status, offValue
        self.title, self.preferred_size = title, size
        self._initial_maximize, self._initial_fullscreen = maximize, fullscreen
        self.open_cb = self.close_cb = None
        self._modal_state = {'open': False, 'generation': 0}

    def open(self, callback, *args, **kwargs):
        self.open_cb = callback, args, kwargs
        return self

    def close(self, callback, *args, **kwargs):
        self.close_cb = callback, args, kwargs
        return self

    def maximize(self, enabled=True):
        self._initial_maximize = enabled
        return self

    def fullscreen(self, enabled=True):
        self._initial_fullscreen = enabled
        return self

    def update(self, prev):
        if prev is not None:
            self._modal_state = prev._modal_state
        super().update(prev)

    def _modal_requested(self):
        if not self._visible or not bool(self.status.value):
            return False
        parent = self.parent
        while parent is not None and parent is not self:
            if not parent._visible:
                return False
            if isinstance(parent, ModalMixin) and not parent._modal_requested():
                return False
            if parent.parent is parent:
                break
            parent = parent.parent
        return True

    def _transition(self, opened):
        if self._modal_state['open'] == opened:
            return
        self._modal_state['open'] = opened
        self._modal_state['generation'] += 1
        callback = self.open_cb if opened else self.close_cb
        if callback:
            fn, args, kwargs = callback
            fn(*args, **kwargs)

    def _dismiss(self):
        node = self.get_node()
        if not node.destroyed and node._modal_state['open']:
            node.status.value = node.offValue
            node._set_modal(False)

    def _set_modal(self, opened):
        raise NotImplementedError

    def postUpdate(self):
        super().postUpdate()
        self._set_modal(self._modal_requested())

    def destroy(self, direct):
        self._set_modal(False)
        super().destroy(True)
