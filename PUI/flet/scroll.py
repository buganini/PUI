from __future__ import annotations
from .. import _typing as _t
from .base import *
import math


class Scroll(FBase):
    END = -0.0

    def __init__(self, vertical: bool | None = None, horizontal: bool | None = False) -> None:
        super().__init__()
        self.vertical, self.horizontal = vertical, horizontal
        self.layout_weight = 1
        self.requests = [None, None]

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui, self.hframe = prev.ui, prev.hframe
            self.scroll_state = prev.scroll_state
        else:
            self.hframe = ft.Row()
            self.ui = ft.Column(controls=[self.hframe])
            self.scroll_state = {'requests': [None, None], 'pending': [None, None], 'task': None}
        for axis, frame in enumerate((self.hframe, self.ui)):
            option = self.horizontal if axis == 0 else self.vertical
            frame.scroll = None if option is False else ft.ScrollMode.AUTO if option is None else ft.ScrollMode.ALWAYS
            request = self.requests[axis]
            if request is not None and request != self.scroll_state['requests'][axis]:
                self.scroll_state['requests'][axis] = request
                self.scroll_state['pending'][axis] = request
                frame.auto_scroll = request == (-1.0, 0)
        super().update(prev)

    def addChild(self, idx, child):
        if idx != 0:
            raise ValueError('Scroll accepts one content widget or layout')
        self.hframe.controls.insert(idx, child.outer)

    def removeChild(self, idx, child):
        self.hframe.controls.pop(idx)

    def scrollX(self, pos=0):
        return self._request(0, pos)

    def scrollY(self, pos=0):
        return self._request(1, pos)

    def _request(self, axis, pos):
        node = self.get_node()
        request = (math.copysign(1, pos), abs(pos))
        node.requests[axis] = request
        if node.ui is not None and not node.destroyed:
            node.scroll_state['requests'][axis] = request
            node.scroll_state['pending'][axis] = request
            (node.hframe if axis == 0 else node.ui).auto_scroll = request == (-1.0, 0)
            node.postSync()
        return self

    def postSync(self):
        app = FView.application(self)
        if app is not None and app.ready and any(value is not None for value in self.scroll_state['pending']):
            task = self.scroll_state['task']
            if task is None or task.done():
                self.scroll_state['task'] = app.ui.run_task(self._apply_scroll)

    async def _apply_scroll(self):
        node = self.get_node()
        for axis in (0, 1):
            if node.destroyed:
                return
            request = node.scroll_state['pending'][axis]
            if request is None:
                continue
            node.scroll_state['pending'][axis] = None
            sign, offset = request
            value = offset if sign > 0 else -offset if offset else -1
            await (node.hframe if axis == 0 else node.ui).scroll_to(offset=value)
            node = node.get_node()

    def destroy(self, direct):
        task = self.scroll_state['task']
        if task is not None:
            task.cancel()
        super().destroy(direct)
