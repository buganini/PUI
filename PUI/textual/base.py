from .. import *
from textual import widgets, containers

class TBase(PUINode):
    scroll = False
    container_x = False # axis
    container_y = False # axis
    expand_x_prio = 0
    expand_y_prio = 0
    expand_x1_children = 0
    expand_x2_children = 0
    expand_x3_children = 0
    expand_x4_children = 0
    expand_y1_children = 0
    expand_y2_children = 0
    expand_y3_children = 0
    expand_y4_children = 0
    cached_tparent = None

    @property
    def expand_x(self):
        parent = self.cached_tparent
        expand = self.expand_x_prio
        if not parent:
            return False

        # textual handles 1fr as shrinkable, but we need scrolller's content not to shrink
        # See Exp.1 in refs/textual_layout.py
        if parent.scroll:
            return False

        # textual populates auto(1fr) to be 1fr(1fr), but we require expanding not to go over the container
        # See Exp.2 in refs/textual_layout.py
        if not parent.expand_x and expand < 3:
            return False

        return expand

    @property
    def expand_y(self):
        parent = self.cached_tparent
        expand = self.expand_y_prio
        if not parent:
            return False

        # textual handles 1fr as shrinkable, but we need scrolller's content not to shrink
        # See Exp.1 in refs/textual_layout.py
        if parent.scroll:
            return False

        # textual populates auto(1fr) to be 1fr(1fr), but we require expanding not to go over the container
        # See Exp.2 in refs/textual_layout.py
        if not parent.expand_y and expand < 3:
            return False

        return expand

    def tremove(self):
        self.ui.remove()

    def destroy(self, direct):
        self.ui.remove()
        return super().destroy(direct)

    def update(self, prev):
        super().update(prev)

        self.cached_tparent = parent = self.tparent
        if parent:
            if self.layout_weight:
                if parent.container_x:
                    self.expand_x_prio = 4
                if parent.container_y:
                    self.expand_y_prio = 4

            if self.expand_x_prio >= 1:
                parent.expand_x1_children += 1
            if self.expand_x_prio >= 2:
                parent.expand_x2_children += 1
            if self.expand_x_prio >= 3:
                parent.expand_x3_children += 1
            if self.expand_x_prio >= 4:
                parent.expand_x4_children += 1

            if self.expand_y_prio >= 1:
                parent.expand_y1_children += 1
            if self.expand_y_prio >= 2:
                parent.expand_y2_children += 1
            if self.expand_y_prio >= 3:
                parent.expand_y3_children += 1
            if self.expand_y_prio >= 4:
                parent.expand_y4_children += 1

    def postUpdate(self):
        super().postUpdate()
        parent = self.cached_tparent
        if parent:
            if parent.container_x:
                if self.expand_x_prio < 1 and parent.expand_x1_children > 0:
                    self.expand_x_prio = 0
                if self.expand_x_prio < 2 and parent.expand_x2_children > 0:
                    self.expand_x_prio = 0
                if self.expand_x_prio < 3 and parent.expand_x3_children > 0:
                    self.expand_x_prio = 0
                if self.expand_x_prio < 4 and parent.expand_x4_children > 0:
                    self.expand_x_prio = 0

            if parent.container_y:
                if self.expand_y_prio < 1 and parent.expand_y1_children > 0:
                    self.expand_y_prio = 0
                if self.expand_y_prio < 2 and parent.expand_y2_children > 0:
                    self.expand_y_prio = 0
                if self.expand_y_prio < 3 and parent.expand_y3_children > 0:
                    self.expand_y_prio = 0
                if self.expand_y_prio < 4 and parent.expand_y4_children > 0:
                    self.expand_y_prio = 0

        self.t_update_layout()

    @property
    def tparent(self):
        parent = self.parent
        while not isinstance(parent, TBase):
            if parent==parent.parent:
                parent = None
                break
            parent = parent.parent
        return parent

    def t_update_layout(self):
        if not self.ui:
            return

        width = "auto"
        if self.expand_x:
            width = "1fr"

        height = "auto"
        if self.expand_y:
            height = "1fr"

        if self._debug:
            print("layout", self.key, f"{width}:{height} expand_x={self.expand_x}", f"expand_y={self.expand_y}", f"expand_x_prio={self.expand_x_prio}", f"expand_y_prio={self.expand_y_prio}")
        self.ui.styles.width = width
        self.ui.styles.height = height

class TPUIView(PUIView):
    pui_virtual = True
