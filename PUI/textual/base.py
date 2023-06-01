from .. import *
from textual import widgets, containers


def get_child_content_width(child):
    if hasattr(child, "content_width"):
        return child.content_width
    elif child.children:
        return get_child_content_width(child.children[0])
    return True

def get_child_content_height(child):
    if hasattr(child, "content_height"):
        return child.content_height
    elif child.children:
        return get_child_content_height(child.children[0])
    return True

class TBase(PUINode):
    container_x = False
    container_y = False

    def tremove(self):
        self.ui.remove()

    def destroy(self, direct):
        self.ui.remove()
        return super().destroy(direct)

    @property
    def tparent(self):
        parent = self.parent
        while not isinstance(parent, TBase):
            if parent==parent.parent:
                parent = None
                break
            parent = parent.parent
        return parent

    @property
    def content_width(self):
        parent = self.tparent
        if parent:
            if parent.container_x and self.layout_weight:
                return False
        return True

    @property
    def content_height(self):
        parent = self.tparent
        if parent:
            if parent.container_y and self.layout_weight:
                return False
        return True

    def t_update_layout(self):
        if not self.ui:
            return

        content_width = self.content_width
        if content_width is None:
            width = ""
        else:
            width = "1fr"
            if content_width:
                width = "auto"
            width = f"width:{width};"
        content_height = self.content_height
        if content_height is None:
            height = ""
        else:
            height = "1fr"
            if content_height:
                height = "auto"
            height = f"height:{height};"
        self.ui.set_styles(width+height)
