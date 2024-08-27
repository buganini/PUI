from .. import *
from textual import widgets, containers

class TBase(PUINode):
    scroll = False
    container_x = False
    container_y = False
    strong_expand_x = False
    strong_expand_y = False
    weak_expand_x = False
    weak_expand_y = False
    nweak_expand_x = False
    nweak_expand_y = False
    strong_expand_x_children = 0
    strong_expand_y_children = 0

    @property
    def expand_x(self):
        return self.strong_expand_x or (self.weak_expand_x and not self.nweak_expand_x)

    @property
    def expand_y(self):
        return self.strong_expand_y or (self.weak_expand_y and not self.nweak_expand_y)

    def tremove(self):
        self.ui.remove()

    def destroy(self, direct):
        self.ui.remove()
        return super().destroy(direct)

    def update(self, prev):
        parent = self.tparent
        if parent:
            if not parent.scroll and len(parent.children) == 1:
                if parent.expand_x:
                    self.strong_expand_x = True
                if parent.expand_y:
                    self.strong_expand_y = True

            # request expanding from inside
            if parent.container_x:
                if parent.expand_y:
                    self.strong_expand_y = True
                if self.layout_weight:
                    self.strong_expand_x = True
                    parent.strong_expand_x_children += 1
                    p = parent
                    while p:
                        if isinstance(p, TBase):
                            p.weak_expand_x = True
                        if p==p.parent:
                            break
                        p = p.parent

            if parent.container_y:
                if parent.expand_x:
                    self.strong_expand_x = True
                if self.layout_weight:
                    self.strong_expand_y = True
                    parent.strong_expand_y_children += 1
                    p = parent
                    while p:
                        if isinstance(p, TBase):
                            p.weak_expand_y = True
                        if p==p.parent:
                            break
                        p = p.parent

            if parent.strong_expand_x_children > 0:
                self.nweak_expand_x = True
            if parent.strong_expand_y_children > 0:
                self.nweak_expand_y = True

        else:
            # mark root node as expanding
            self.strong_expand_x = True
            self.strong_expand_y = True

        super().update(prev)

    def postUpdate(self):
        super().postUpdate()
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
            print("layout", self.key, f"{width}:{height} expand_x={self.expand_x}", f"expand_y={self.expand_y}", f"strong_x={self.strong_expand_x}", f"weak_x={self.weak_expand_x}", f"hug_x={self.nweak_expand_x}", f"strong_y={self.strong_expand_y}", f"weak_y={self.weak_expand_y}", f"hug_y={self.nweak_expand_y}")
        self.ui.set_styles(f"width:{width};height:{height};")

class TPUIView(PUIView):
    pui_virtual = True
