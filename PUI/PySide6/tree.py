from .. import *
from .base import *
from PySide6.QtCore import Qt, QModelIndex, QAbstractItemModel

class QAbstractItemModelAdapter(QtCore.QAbstractItemModel):
    def __init__(self, model: "BaseTreeAdapter"):
        super().__init__()
        self.model = model

    def index(self, row, column, parent = QtCore.QModelIndex()):
        parent_node = parent.internalPointer() if parent.isValid() else None
        if 0 <= row and row < self.model.rowCount(parent_node):
            child = self.model.child(parent_node, row)
            return self.createIndex(row, column, child)
        return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        parent_node = self.model.parent(node)
        if parent_node:
            return self.createIndex(0, 0, parent_node)
        return QModelIndex()

    def data(self, index, role):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            return self.model.data(node)
        return None

    def rowCount(self, parent):
        parent_node = parent.internalPointer() if parent.isValid() else None
        return self.model.rowCount(parent_node)

    def columnCount(self, parent):
        return 1

    def hasChildren(self, parent):
        parent_node = parent.internalPointer() if parent.isValid() else None
        return self.model.rowCount(parent_node) > 0


class Tree(QtBaseWidget):
    def __init__(self, model):
        super().__init__()
        self.layout_weight = 1
        self.model = model
        self.curr_model = None

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qt_model = prev.qt_model
            self.curr_model = prev.curr_model
        else:
            self.qt_model = None
            self.curr_model = Prop()
            self.ui = QtWidgets.QTreeView()
            self.ui.setHeaderHidden(True)

        if self.curr_model.set(self.model):
            self.qt_model = QAbstractItemModelAdapter(self.model)
            self.ui.setModel(self.qt_model)
        else:
            self.qt_model.dataChanged.emit(QModelIndex(), QModelIndex())

        self.ui.clicked.connect(self.on_item_clicked)
        self.ui.doubleClicked.connect(self.on_item_double_clicked)
        super().update(prev)

    def on_item_clicked(self, index):
        node = index.internalPointer()
        self.model.clicked(node)

    def on_item_double_clicked(self, index):
        node = index.internalPointer()
        self.model.dblclicked(node)