from ..grid import GridMixin, native_stretches
from ..adaptive import BoxMixin as _BoxMixin, HVBoxMixin as _HVBoxMixin, VHBoxMixin as _VHBoxMixin
from .. import *
from .base import *

class Stack(QtBaseLayout):
    expand_x_prio = expand_y_prio = 3
    pui_terminal = False
    pui_reversed_order = True

    def __init__(self):
        super().__init__()
        self.qt_params = {}
        if not isinstance(self.non_virtual_parent, QtBaseLayout):
            self.layout_padding = (11,11,11,11)

    @property
    def outer(self):
        return self.ui

    @property
    def inner(self):
        return self.layout

    def destroy(self, direct):
        self.layout = None
        super().destroy(direct)

    def update(self, prev=None):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qtlayout = prev.qtlayout
        else:
            self.ui = QtWidgets.QWidget()
            self.qtlayout = QtWidgets.QStackedLayout()
            self.qtlayout.setStackingMode(QtWidgets.QStackedLayout.StackAll)
            self.qtlayout.setContentsMargins(0,0,0,0)
            self.ui.setLayout(self.qtlayout)
        super().update(prev)

    def addChild(self, idx, child):
        from .modal import Modal
        from .layout import Spacer
        if isinstance(child, Spacer):
            pass
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            self.qtlayout.insertWidget(idx, child.outer)
            self.mounted_children.insert(idx, child)

    def removeChild(self, idx, child):
        from .modal import Modal
        from .layout import Spacer
        if isinstance(child, Spacer):
            pass
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
            self.mounted_children.pop(idx)

    def postUpdate(self):
        if self.ui:
            if self._onDropped:
                self.ui.setAcceptDrops(True)
                self.ui.installEventFilter(self.eventFilter)
            else:
                self.ui.setAcceptDrops(False)

        super().postUpdate()

def _box_direction(node):
    directions = ((QtWidgets.QBoxLayout.LeftToRight, QtWidgets.QBoxLayout.RightToLeft)
                  if node.container_x else
                  (QtWidgets.QBoxLayout.TopToBottom, QtWidgets.QBoxLayout.BottomToTop))
    node.qtlayout.setDirection(directions[node._inverse])


class HBox(_BoxMixin, QtBaseLayout):
    expand_x_prio = 3
    expand_y_prio = 1
    _native_box_inverse = True
    container_x = True
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qtlayout = prev.qtlayout
        else:
            self.ui = QtWidgets.QWidget()
            self.qtlayout = QtWidgets.QHBoxLayout()
            self.qtlayout.setContentsMargins(0,0,0,0)
            self.ui.setLayout(self.qtlayout)
        super().update(prev)
        _box_direction(self)

class VBox(_BoxMixin, QtBaseLayout):
    expand_x_prio = 1
    expand_y_prio = 3
    _native_box_inverse = True
    container_y = True
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qtlayout = prev.qtlayout
        else:
            self.ui = QtWidgets.QWidget()
            self.qtlayout = QtWidgets.QVBoxLayout()
            self.qtlayout.setContentsMargins(0,0,0,0)
            self.ui.setLayout(self.qtlayout)
        super().update(prev)
        _box_direction(self)

class Spacer(PUINode):
    pui_terminal = True
    pui_movable = False

    def __init__(self):
        super().__init__()
        self.layout_weight = 1

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            if getattr(self.non_virtual_parent, 'container_y', False):
                self.ui = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
            elif getattr(self.non_virtual_parent, 'container_x', False):
                self.ui = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            else:
                self.ui = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        policy = QtWidgets.QSizePolicy
        horizontal = policy.Preferred if getattr(self.non_virtual_parent, 'container_y', False) else policy.Expanding
        vertical = policy.Preferred if getattr(self.non_virtual_parent, 'container_x', False) else policy.Expanding
        self.ui.changeSize(0, 0, horizontal if self._visible else policy.Fixed,
                           vertical if self._visible else policy.Fixed)
        super().update(prev)

    def destroy(self, direct):
        # self.ui.deleteLater() # QSpacerItem doesn't have .deleteLater()
        super().destroy(direct)

class Grid(GridMixin, QtBaseLayout):
    expand_x_prio = expand_y_prio = 1
    pui_grid_layout = True

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.layout = prev.layout
            self.mounted = prev.mounted
        else:
            self.mounted = []
            self.ui = QtWidgets.QWidget()
            self.layout = QtWidgets.QGridLayout()
            self.layout.setContentsMargins(0,0,0,0)
            self.ui.setLayout(self.layout)
        super().update(prev)

    def addChild(self, idx, child):
        self.mounted.insert(idx, child)

    def removeChild(self, idx, child):
        self.mounted.pop(idx)
        if isinstance(child.outer, QtWidgets.QSpacerItem):
            self.layout.removeItem(child.outer)
        else:
            self.layout.removeWidget(child.outer)

    def postSync(self):
        cells = self.grid_cells(self.mounted)
        columns, rows = self.grid_stretches(cells)
        columns, rows = native_stretches(columns), native_stretches(rows)
        while self.layout.count():
            self.layout.takeAt(0)
        for column in range(max(self.layout.columnCount(), len(columns))):
            self.layout.setColumnStretch(column, int(columns[column]) if column < len(columns) else 0)
        for row in range(max(self.layout.rowCount(), len(rows))):
            self.layout.setRowStretch(row, int(rows[row]) if row < len(rows) else 0)
        flags = QtCore.Qt.AlignmentFlag
        self.layout.setAlignment((flags(0) if any(columns) else flags.AlignLeft) |
                                 (flags(0) if any(rows) else flags.AlignTop))
        for child, (row, column, rowspan, columnspan) in cells:
            if isinstance(child.outer, QtWidgets.QSpacerItem):
                self.layout.addItem(child.outer, row, column, rowspan, columnspan)
            else:
                # Track growth and cell fill are separate: a compact control
                # keeps its size even when another child enlarges its track.
                alignment = ((flags(0) if child._layout_priority(True) > 0 else flags.AlignLeft) |
                             (flags(0) if child._layout_priority(False) > 0 else flags.AlignVCenter))
                policy = child.outer.sizePolicy()
                policy.setHorizontalPolicy(child.qt_params.get('HorizontalPolicy', QtWidgets.QSizePolicy.Preferred))
                policy.setVerticalPolicy(child.qt_params.get('VerticalPolicy', QtWidgets.QSizePolicy.Preferred))
                child.outer.setSizePolicy(policy)
                self.layout.addWidget(child.outer, row, column, rowspan, columnspan, alignment)
        super().postSync()

class _AdaptiveLayout(HBox):
    pass


class HVBox(_HVBoxMixin, _AdaptiveLayout):
    pass


class VHBox(_VHBoxMixin, _AdaptiveLayout):
    pass
