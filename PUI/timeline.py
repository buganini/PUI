from threading import Timer
from .view import *

class TimelineView(PUINode):
    pui_virtual = True
    def __init__(self, ttl_sec):
        super().__init__()
        self.timer = None
        self.ttl_sec = ttl_sec

    def update(self, prev):
        super().update(prev)
        if prev and hasattr(prev, "timer"):
            self.timer = prev.timer
        else:
            self.timer = self._schedule()

    def _schedule(self):
        timer = Timer(self.ttl_sec, self.timer_cb)
        timer.daemon = True
        timer.start()
        return timer

    def timer_cb(self):
        node = self.get_node()
        if node.destroyed or not node.timer:
            return
        root = node.root
        if not root:
            return
        root.redraw()
        node.timer = node._schedule()

    def destroy(self, direct):
        timer = self.timer
        self.timer = None
        if timer:
            timer.cancel()
        super().destroy(direct)
