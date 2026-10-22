"""Per-axis demand propagation, boundaries and live virtual subtrees."""
import unittest
from PUI.node import PUINode
from PUI.expansion import priority


def node(parent=None, x=1, y=1, virtual=False, **settings):
    result=PUINode()
    result.parent=parent
    result.children=[]
    result.expand_x_prio=x
    result.expand_y_prio=y
    result.pui_virtual=virtual
    for name,value in settings.items():
        setattr(result,name,value)
    if parent is not None:
        parent.children.append(result)
    return result


class ExpansionTests(unittest.TestCase):
    def test_nested_demand_and_withdrawal(self):
        root=node(container_x=True)
        box=node(root)
        view=node(box,virtual=True)
        inner=node(view)
        leaf=node(inner,x=4,y=0)
        self.assertEqual(priority(box,'x'),2)
        self.assertEqual(priority(box,'y'),1)
        leaf._visible=False
        self.assertEqual(priority(box,'x'),1)
        leaf._visible=True
        self.assertEqual(priority(box,'x'),2)
        inner.children.clear()
        self.assertEqual(priority(box,'x'),1)

    def test_weight_and_fixed_boundaries(self):
        root=node(container_x=True)
        box=node(root,container_x=True)
        leaf=node(box,x=0,y=0,layout_weight=9)
        self.assertEqual(priority(leaf,'x'),5)
        self.assertEqual(priority(box,'x'),2)
        box.layout_weight=0
        self.assertEqual(priority(box,'x'),0)
        box.layout_weight=None
        box.layout_width=100
        self.assertEqual(priority(box,'x'),1)
        box.layout_width=None
        box.tlayout_weight=0
        box._terminal_units=True
        self.assertEqual(priority(box,'x'),0)

    def test_main_axis_and_shrinkable_priorities_are_not_promoted(self):
        root=node(container_x=True)
        for base in (3,4):
            box=node(root,x=base,container_x=True)
            node(box,layout_weight=10)
            self.assertEqual(priority(box,'x'),base)
