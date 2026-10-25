"""Binding and event lifecycle shared by native multiline editors."""
from .node import PUIEvent


class TextEditBinding:
    def _sync_text(self, prev):
        self.editing = prev.editing if prev is not None else False
        if self.readonly:
            self.editing = False
        if not self.editing:
            value = str(self.model.value)
            self._set_text(value)
            if self.edit_model is not None:
                self.edit_model.value = value

    def _input_text(self, value):
        node = self.get_node()
        if node.destroyed or node.readonly:
            return
        node.editing = True
        if node.edit_model is not None:
            node.edit_model.value = value
        event = PUIEvent()
        event.value = value
        node._input(event)

    def _commit_text(self, value):
        node = self.get_node()
        if node.destroyed or node.readonly or not node.editing:
            return
        node.editing = False
        node.model.value = value
        normalized = str(node.model.value)
        node._set_text(normalized)
        if node.edit_model is not None:
            node.edit_model.value = normalized
        event = PUIEvent()
        event.value = value
        node._change(event)
