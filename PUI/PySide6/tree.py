from .. import *
from .base import *
from PySide6.QtCore import Qt, QModelIndex, QAbstractItemModel

class QAbstractItemModelAdapter(QtCore.QAbstractItemModel):
    def __init__(self, model: "BaseTreeAdapter"):
        super().__init__()
        self.model = model
        self.node = None

    def index(self, row, column, parent = QtCore.QModelIndex()):
        parent_node = parent.internalPointer() if parent.isValid() else None
        if 0 <= row and row < self.model.rowCount(parent_node):
            child = self.model.child(parent_node, row)
            return self.createIndex(row, column, child)
        return QtCore.QModelIndex()

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsDropEnabled

        defaultFlags = super().flags(index)

        return defaultFlags | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled

    def canDropMimeData(self, data, action, row, column, parent):
        if parent.isValid():
            pass
        else:
            return bool(self.node._onDropped)

    def dropMimeData(self, data, action, row, column, parent):
        if parent.isValid():
            pass
        else:
            event = QtGui.QDropEvent(QtCore.QPoint(0,0), action, data, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier, QtCore.QEvent.Drop)
            self.node._onDropped[0](event, *self.node._onDropped[1], **self.node._onDropped[2])

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

    def clicked(self, node):
        self.model.clicked(node)

    def dblclicked(self, node):
        self.model.dblclicked(node)

    def expanded(self, node):
        self.model.expanded(node)

    def collapsed(self, node):
        self.model.collapsed(node)

class QTreeNodeModelAdapter(QtCore.QAbstractItemModel):
    def __init__(self):
        super().__init__()
        self.node = None

    def index(self, row, column, parent = QtCore.QModelIndex()):
        parent_node = self.resolve(parent.internalPointer()) if parent.isValid() else self.node
        if 0 <= row and row < len(parent_node.children):
            child = parent_node.children[row]
            return self.createIndex(row, column, child)
        return QtCore.QModelIndex()

    @staticmethod
    def resolve(node):
        return node.get_node() if node else None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsDropEnabled

        defaultFlags = super().flags(index)

        return defaultFlags | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled

    def canDropMimeData(self, data, action, row, column, parent):
        if parent.isValid():
            pass
        else:
            return bool(self.node._onDropped)

    def dropMimeData(self, data, action, row, column, parent):
        if parent.isValid():
            pass
        else:
            event = QtGui.QDropEvent(QtCore.QPoint(0,0), action, data, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier, QtCore.QEvent.Drop)
            self.node._onDropped[0](event, *self.node._onDropped[1], **self.node._onDropped[2])

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node = self.resolve(index.internalPointer())
        parent_node = node.parent
        if not isinstance(parent_node, TreeNode):
            parent_node = None
        if parent_node:
            try:
                row = parent_node.parent.children.index(parent_node)
            except (AttributeError, ValueError):
                return QModelIndex()
            return self.createIndex(row, 0, parent_node)
        return QModelIndex()

    def data(self, index, role):
        if not index.isValid():
            return None
        node = self.resolve(index.internalPointer())
        if role == QtCore.Qt.DisplayRole:
            return node.data
        return None

    def rowCount(self, parent):
        parent_node = self.resolve(parent.internalPointer()) if parent.isValid() else self.node
        return len(parent_node.children)

    def columnCount(self, parent):
        return 1

    def hasChildren(self, parent):
        parent_node = self.resolve(parent.internalPointer()) if parent.isValid() else self.node
        return len(parent_node.children) > 0

    def clicked(self, node):
        self.resolve(node)._clicked(None)

    def dblclicked(self, node):
        self.resolve(node)._dblclicked(None)

    def expanded(self, node):
        self.resolve(node)._expanded()

    def collapsed(self, node):
        self.resolve(node)._collapsed()

class Tree(QtBaseWidget):
    # TreeNode children back QModelIndex internal pointers, so they must take
    # part in DOM sync to link retired nodes to their replacements.
    pui_terminal = False

    @staticmethod
    def emitDataChanged(model, parent=QtCore.QModelIndex()):
        row_count = model.rowCount(parent)
        column_count = model.columnCount(parent)
        if row_count == 0 or column_count == 0:
            return

        first = model.index(0, 0, parent)
        last = model.index(row_count - 1, column_count - 1, parent)
        model.dataChanged.emit(first, last, [QtCore.Qt.DisplayRole])

        for row in range(row_count):
            Tree.emitDataChanged(model, model.index(row, 0, parent))

    def __init__(self, model=None):
        super().__init__()
        self.layout_weight = 1
        self.model = model
        self.curr_model = None
        self.pendings = []
        self._expand_callback = None
        self._collapse_callback = None
        self._tree_sync_pending = False
        self._previous_tree = None
        self._old_index_nodes = []
        self._persistent_indexes = []

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qt_model = prev.qt_model
            self.curr_model = prev.curr_model

            self.ui.clicked.disconnect()
            self.ui.doubleClicked.disconnect()
            self.ui.expanded.disconnect()
            self.ui.collapsed.disconnect()
        else:
            self.qt_model = None
            self.curr_model = Prop()
            self.ui = QtWidgets.QTreeView()
            self.ui.setHeaderHidden(True)

        self.ui.clicked.connect(self.on_item_clicked)
        self.ui.doubleClicked.connect(self.on_item_double_clicked)
        self.ui.expanded.connect(self.on_item_expanded)
        self.ui.collapsed.connect(self.on_item_collapsed)

        if self.model:
            if self.curr_model.set(self.model):
                self.qt_model = QAbstractItemModelAdapter(self.model)
                self.qt_model.node = self
                self.ui.setModel(self.qt_model)
            else:
                self.emitDataChanged(self.qt_model)
        else:
            if not isinstance(self.qt_model, QTreeNodeModelAdapter):
                self.qt_model = QTreeNodeModelAdapter()
                self.qt_model.node = self
                self.ui.setModel(self.qt_model)
            else:
                # TreeNode children are reconciled immediately after update().
                # Keep the model on the old tree until preSync(), then notify Qt
                # about the layout change around that reconciliation.
                self._tree_sync_pending = True
                self._previous_tree = prev

        if not self._tree_sync_pending:
            self._run_pendings()

        super().update(prev)

    def _run_pendings(self):
        for pending in self.pendings:
            pending[0](*pending[1:])
        self.pendings = []

    @staticmethod
    def _collect_tree_nodes(node):
        nodes = []
        pending = list(node.children) if node else []
        while pending:
            child = pending.pop()
            if isinstance(child, TreeNode):
                nodes.append(child)
                pending.extend(child.children)
        return nodes

    def preSync(self):
        if self._tree_sync_pending:
            self._old_index_nodes = self._collect_tree_nodes(self._previous_tree)
            self.qt_model.layoutAboutToBeChanged.emit()
            self._persistent_indexes = list(self.qt_model.persistentIndexList())
            self.qt_model.node = self
        super().preSync()

    def postSync(self):
        if self._tree_sync_pending:
            new_nodes = set(self._collect_tree_nodes(self))
            new_indexes = []

            for old_index in self._persistent_indexes:
                old_node = old_index.internalPointer()
                new_node = old_node.get_node() if old_node else None
                if new_node not in new_nodes:
                    new_indexes.append(QModelIndex())
                    continue

                try:
                    row = new_node.parent.children.index(new_node)
                except (AttributeError, ValueError):
                    new_indexes.append(QModelIndex())
                    continue

                new_indexes.append(
                    self.qt_model.createIndex(row, old_index.column(), new_node)
                )

            try:
                self.qt_model.changePersistentIndexList(
                    self._persistent_indexes,
                    new_indexes,
                )
            finally:
                self.qt_model.layoutChanged.emit()
                self._tree_sync_pending = False
                self._previous_tree = None
                self._old_index_nodes = []
                self._persistent_indexes = []
            self._run_pendings()
        super().postSync()

    def expandAll(self):
        if self.ui:
            self.ui.expandAll()
        else:
            self.pendings.append([self.expandAll])
        return self

    def collapseAll(self):
        if self.ui:
            self.ui.collapseAll()
        else:
            self.pendings.append([self.collapseAll])
        return self

    def expandable(self, enabled):
        if self.ui:
            self.ui.setItemsExpandable(enabled)
        else:
            self.pendings.append([self.expandable, enabled])
        return self

    def expand(self, cb, *args, **kwargs):
        self._expand_callback = (cb, args, kwargs)
        return self

    def _expanded(self):
        if self._expand_callback:
            cb, args, kwargs = self._expand_callback
            cb(*args, **kwargs)

    def collapse(self, cb, *args, **kwargs):
        self._collapse_callback = (cb, args, kwargs)
        return self

    def _collapsed(self):
        if self._collapse_callback:
            cb, args, kwargs = self._collapse_callback
            cb(*args, **kwargs)

    def on_item_clicked(self, index):
        treenode = index.internalPointer()
        self.get_node().qt_model.clicked(treenode)

    def on_item_double_clicked(self, index):
        treenode = index.internalPointer()
        self.get_node().qt_model.dblclicked(treenode)

    def on_item_expanded(self, index):
        treenode = index.internalPointer()
        self.get_node().qt_model.expanded(treenode)

    def on_item_collapsed(self, index):
        treenode = index.internalPointer()
        self.get_node().qt_model.collapsed(treenode)

class TreeNode(PUINode):
    def __init__(self, data=""):
        super().__init__()
        self._set_callback = None
        self.data = data
        self._expand_callback = None
        self._collapse_callback = None

    def expand(self, cb, *args, **kwargs):
        self._expand_callback = (cb, args, kwargs)
        return self

    def _expanded(self):
        if self._expand_callback:
            cb, args, kwargs = self._expand_callback
            cb(*args, **kwargs)

    def collapse(self, cb, *args, **kwargs):
        self._collapse_callback = (cb, args, kwargs)
        return self

    def _collapsed(self):
        if self._collapse_callback:
            cb, args, kwargs = self._collapse_callback
            cb(*args, **kwargs)
