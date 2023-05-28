from .. import *
import flet as ft

def _apply_params(ui, params):
    for k,v in params.items():
        setattr(ui, k, v)
class FBase(PUINode):
    def __init__(self, *args):
        super().__init__(*args)
        self.child_weight = None
        if self.fparent:
            self.layout_weight = self.fparent.child_weight

        self.flet_params = {}

    def flet(self, **kwargs):
        for k,v in kwargs.items():
            self.flet_params[k] = v
        return self

    def update(self, prev):
        _apply_params(self.ui, self.flet_params)
        super().update(prev)

    @property
    def fparent(self):
        parent = self.parent
        while True:
            if isinstance(parent, FBase):
                return parent
            if parent.parent == parent:
                return None
            parent = parent.parent
