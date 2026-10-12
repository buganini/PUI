from .base import *
import math
import wx.lib.scrolledpanel as scrolled


class Scroll(WxSingleChild):
    scroll = True
    END = -0.0

    def __init__(self, vertical=None, horizontal=False):
        super().__init__()
        self.vertical = vertical
        self.horizontal = horizontal
        self.positions = [0, 0]
        self.requests = [None, None]
        self.pending = False

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.positions = list(prev.positions)
            self.pending = prev.pending
            for axis in (0, 1):
                if self.requests[axis] is not None and self.requests[axis] != prev.requests[axis]:
                    self.positions[axis] = self.requests[axis]
                    self.pending = True
                elif self.requests[axis] is None:
                    self.requests[axis] = prev.requests[axis]
            self.ui.Unbind(wx.EVT_SIZE, handler=prev.on_size)
        else:
            self.ui = scrolled.ScrolledPanel(getWindow(self.parent))
            self.positions = [r if r is not None else 0 for r in self.requests]
            self.pending = any(r is not None for r in self.requests)
        self.ui.Bind(wx.EVT_SIZE, self.on_size)
        self.container_y = self.vertical is not False
        self.container_x = self.horizontal is not False
        self.expand_y_prio = 3 if self.container_y else 1
        self.expand_x_prio = 3 if self.container_x else 1
        super().update(prev)

    def scrollX(self, pos=0):
        return self._request(0, pos)

    def scrollY(self, pos=0):
        return self._request(1, pos)

    def _request(self, axis, pos):
        self.requests[axis] = (math.copysign(1, pos), abs(pos))
        self.positions[axis] = self.requests[axis]
        self.pending = True
        if self.ui:
            wx.CallAfter(self.restore)
        return self

    def maximum(self, axis):
        orientation = wx.HORIZONTAL if axis == 0 else wx.VERTICAL
        return max(0, self.ui.GetScrollRange(orientation) - self.ui.GetScrollThumb(orientation))

    def preSync(self):
        if self.pending:
            return
        for axis, value in enumerate(self.ui.GetViewStart()):
            maximum = self.maximum(axis)
            position = self.positions[axis]
            sign = position[0] if isinstance(position, tuple) else 1
            if maximum > 20:
                if value <= 10:
                    sign = 1
                elif value >= maximum - 10:
                    sign = -1
            self.positions[axis] = (sign, value if sign > 0 else maximum - value)

    def postSync(self):
        super().postSync()
        self.ui.SetScrollRate(1 if self.horizontal is not False else 0,
                              1 if self.vertical is not False else 0)
        self.ui.ShowScrollbars(self.policy(self.horizontal), self.policy(self.vertical))
        self.ui.FitInside()
        self.restore()
        wx.CallAfter(self.restore)

    @staticmethod
    def policy(value):
        return wx.SHOW_SB_DEFAULT if value is None else wx.SHOW_SB_ALWAYS if value else wx.SHOW_SB_NEVER

    def restore(self):
        node = self.get_node()
        if node.destroyed or not node.ui:
            return
        values = []
        for axis, position in enumerate(node.positions):
            sign, offset = position if isinstance(position, tuple) else (1, position)
            maximum = node.maximum(axis)
            value = offset if sign > 0 else maximum - offset
            values.append(max(0, min(maximum, int(value))))
        node.ui.Scroll(*values)
        node.pending = False

    def on_size(self, event):
        event.Skip()
        node = self.get_node()
        if not node.destroyed and node.ui:
            wx.CallAfter(node.restore)
