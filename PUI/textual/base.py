from .. import *
from textual import widgets, containers


def get_child_content_width(child):
    if hasattr(child, "content_width"):
        return child.content_width
    else:
        return get_child_content_width(child.children[0])

def get_child_content_height(child):
    if hasattr(child, "content_height"):
        return child.content_height
    else:
        return get_child_content_height(child.children[0])

def free_child_width(child):
    todo = [child]
    while todo:
        n = todo.pop(0)
        n.content_width = False
        if hasattr(n, "t_update_layout"):
            n.t_update_layout()
        todo.extend(n.children)

def free_child_height(child):
    todo = [child]
    while todo:
        n = todo.pop(0)
        n.content_height = False
        if hasattr(n, "t_update_layout"):
            n.t_update_layout()
        todo.extend(n.children)

class TBase(PUINode):
    content_width = True
    content_height = True

    def tremove(self):
        self.ui.remove()

    def destroy(self, direct):
        self.ui.remove()
        return super().destroy(direct)

    def t_update_layout(self):
        if not self.ui:
            return
        if self.content_width is None:
            width = ""
        else:
            width = "1fr"
            if self.content_width:
                width = "auto"
            width = f"width:{width};"
        if self.content_height is None:
            height = ""
        else:
            height = "1fr"
            if self.content_height:
                height = "auto"
            height = f"height:{height};"
        self.ui.set_styles(width+height)
