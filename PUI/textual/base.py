from .. import *
from textual import widgets, containers


def get_child_content_width(child):
    if hasattr(child, "fit_content_width"):
        return child.fit_content_width
    elif child.children:
        return get_child_content_width(child.children[0])
    return True

def get_child_content_height(child):
    if hasattr(child, "fit_content_height"):
        return child.fit_content_height
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
    def local_fit_content_width(self):
        parent = self.tparent
        if parent:
            if parent.container_x and self.layout_weight:
                return False
        return True

    @property
    def local_fit_content_height(self):
        parent = self.tparent
        if parent:
            if parent.container_y and self.layout_weight:
                return False
        return True

    @property
    def fit_content_width(self):
        return self.local_fit_content_width

    @property
    def fit_content_height(self):
        return self.local_fit_content_height

    @property
    def fill_parent_width(self):
        node = self
        while node:
            if isinstance(node, TBase):
                if not node.local_fit_content_width:
                    return True
            if node.parent == node:
                break
            node = node.parent
        return False

    @property
    def fill_parent_height(self):
        node = self
        while node:
            if isinstance(node, TBase):
                if not node.local_fit_content_height:
                    return True
            if node.parent == node:
                break
            node = node.parent
        return False

    def t_update_layout(self):
        if not self.ui:
            return

        fit_content_width = self.fit_content_width and not self.fill_parent_width
        width = "1fr"
        if fit_content_width:
            width = "auto"
        width = f"width:{width};"
        fit_content_height = self.fit_content_height and not self.fill_parent_height
        height = "1fr"
        if fit_content_height:
            height = "auto"
        height = f"height:{height};"
        self.ui.set_styles(width+height)
