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
    def fit_content_width(self):
        parent = self.tparent
        if parent:
            if parent.container_x and self.layout_weight:
                if self._debug:
                    print("fit_content_width", False)
                return False
        if self._debug:
            print("fit_content_width", True)
        return True

    @property
    def fit_content_height(self):
        parent = self.tparent
        if parent:
            if parent.container_y and self.layout_weight:
                return False
        return True

    def t_update_layout(self):
        if not self.ui:
            return

        fit_content_width = self.fit_content_width
        if fit_content_width is None:
            width = ""
        else:
            width = "1fr"
            if fit_content_width:
                width = "auto"
            width = f"width:{width};"
        fit_content_height = self.fit_content_height
        if fit_content_height is None:
            height = ""
        else:
            height = "1fr"
            if fit_content_height:
                height = "auto"
            height = f"height:{height};"
        self.ui.set_styles(width+height)
