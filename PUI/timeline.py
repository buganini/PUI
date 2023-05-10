from threading import Timer
from .view import *

class TimelineView(PUINode):
    cbmap = {}
    def __init__(self, ttl_sec):
        super().__init__()
        self.timer = None
        self.ttl_sec = ttl_sec

    def update(self, prev):
        if prev and hasattr(prev, "timer"):
            self.timer = prev.timer
            TimelineView.cbmap[self.timer] = self
        else:
            self.timer = Timer(self.ttl_sec, self.timer_cb)
            TimelineView.cbmap[self.timer] = self
            self.timer.start()

    def timer_cb(self):
        if not self.timer:
            return
        node = TimelineView.cbmap[self.timer] # node is changed in update()
        del TimelineView.cbmap[self.timer]
        root = node.root
        if not root:
            return
        root.redraw()
        node.timer = Timer(self.ttl_sec, self.timer_cb)
        TimelineView.cbmap[self.timer] = node
        node.timer.start()

    @property
    def ui(self):
        return self.children[0].ui

    @ui.setter
    def ui(self, new_ui):
        pass

    def destroy(self, direct):
        timer = self.timer
        self.timer = None
        if timer:
            timer.cancel()
        super().destroy(direct)

    def addChild(self, idx, child):
        self.parent.addChild(idx, child)

    def removeChild(self, idx, child):
        self.parent.removeChild(idx, child)
