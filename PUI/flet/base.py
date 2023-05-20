from .. import *
import flet as ft

def _apply_params(ui, params):
    for k,v in params.items():
        setattr(ui, k, v)
class FBase(PUINode):
    def __init__(self, *args):
        super().__init__(*args)
        self.flet_params = {}

    def flet(self, **kwargs):
        for k,v in kwargs.items():
            self.flet_params[k] = v
        return self

    def update(self, prev):
        _apply_params(self.ui, self.flet_params)
        super().update(prev)

def find_flet_outer(node):
    if isinstance(node, FBase):
        return node.outer
    else:
        return find_flet_outer(node.children[0])