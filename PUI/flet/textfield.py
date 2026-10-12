from .. import *
from .base import *

class TextField(FBase):
    def __init__(self, model, edit_model=None, label="", **kwargs):
        super().__init__()
        self.flet(**kwargs)
        self.model = model
        self.label = label
        self.edit_model = edit_model
        self.editing = False

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.editing = prev.editing
            self.ui = prev.ui
            self.curr_value = prev.curr_value
            if not self.editing and self.curr_value.set(model_value):
                self.ui.value = model_value
        else:
            self.curr_value = Prop(model_value)
            self.ui = ft.TextField(label=self.label, value=model_value, on_change=self.on_textbox_changed, on_blur=self.on_blur, on_submit=self.on_submit, expand=self.layout_weight)

        self.ui.label = self.label
        self.ui.on_change = self.on_textbox_changed
        self.ui.on_focus = self.on_focus
        self.ui.on_blur = self.on_blur
        self.ui.on_submit = self.on_submit
        self.ui.expand = self.layout_weight

        if self.edit_model and not self.editing:
            self.edit_model.value = model_value

        super().update(prev)

    def on_textbox_changed(self, e): # editing
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        node.editing = True
        value = e.control.value
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        node._input(e)

    def on_change(self, e=None): # finish editing
        node = self.get_node()
        if node.destroyed or not node.editing:
            return
        node.editing = False
        value = node.ui.value
        node.model.value = value
        node.ui.value = str(node.model.value)
        node.curr_value.set(node.ui.value)
        if node.edit_model:
            node.edit_model.value = value
        e = PUIEvent()
        e.value = value
        node._change(e)

    def on_focus(self, event):
        node = self.get_node()
        app = FView.application(node)
        if app is not None:
            app.focused_editor = node

    def on_blur(self, e):
        self.on_change(e)
        app = FView.application(self.get_node())
        if app is not None and app.focused_editor is not None and app.focused_editor.get_node() is self.get_node():
            app.focused_editor = None

    def on_submit(self, e):
        self.on_change(e)
