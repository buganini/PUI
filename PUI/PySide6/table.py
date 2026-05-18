from .. import *
from .base import *

class QtTableModelAdapter(QtCore.QAbstractTableModel):
    def __init__(self, pui_node: "Table"):
        super().__init__()
        self.pui_node = pui_node
        self.model = pui_node.model

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            return self.model.data(index.row(), index.column())
        elif role == QtCore.Qt.EditRole:
            return self.model.editData(index.row(), index.column())

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            self.model.setData(index.row(), index.column(), value)
            return True

    def flags(self, index):
        flags = super().flags(index)
        if self.model.editable(index.row(), index.column()):
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if hasattr(self.model, "columnHeader"):
                    if self.model.columnHeader is None:
                        if self.pui_node.columnHeader:
                            return self.pui_node.columnHeader[section]
                        else:
                            return None
                    else:
                        return self.model.columnHeader(section)
                else:
                    return super().headerData(section, orientation, role)
            else:
                if hasattr(self.model, "rowHeader"):
                    if self.model.rowHeader is None:
                        if self.pui_node.rowHeader:
                            return self.pui_node.rowHeader[section]
                        else:
                            return None
                    else:
                        return self.model.rowHeader(section)
                else:
                    return super().headerData(section, orientation, role)

    def rowCount(self, index):
        return self.model.rowCount()

    def columnCount(self, index):
        return self.model.columnCount()

    def clicked(self, index):
        self.model.clicked(index.row(), index.column())

    def dblclicked(self, index):
        self.model.dblclicked(index.row(), index.column())


class QtTableNodeModelAdapter(QtCore.QAbstractTableModel):
    def __init__(self, pui_node):
        super().__init__()
        self.pui_node = pui_node
        self.children = pui_node.children

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            data = self.children[index.row()].children[index.column()].data
            if isinstance(data, BaseBinding):
                return str(data.value)
            return data
        return None

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            n = self.children[index.row()].children[index.column()]
            if isinstance(n.data, BaseBinding):
                n.data.value = value
            else:
                n._set(value)
            return True

    def flags(self, index):
        flags = super().flags(index)
        n = self.children[index.row()].children[index.column()]
        if isinstance(n.data, BaseBinding) or n._set_callback:
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if self.pui_node.columnHeader:
                    return self.pui_node.columnHeader[section]
                else:
                    return super().headerData(section, orientation, role)
            else:
                if self.pui_node.rowHeader:
                    return self.pui_node.rowHeader[section]
                else:
                    return super().headerData(section, orientation, role)

    def rowCount(self, index):
        return len(self.children)

    def columnCount(self, index):
        if self.children:
            return len(self.children[0].children)
        return 0

    def clicked(self, index):
        node = self.children[index.row()].children[index.column()]
        node._clicked(None)

    def dblclicked(self, index):
        node = self.children[index.row()].children[index.column()]
        node._dblclicked(None)

class Table(QtBaseWidget):
    def __init__(self, model=None, autofit=True, columnHeader=None, rowHeader=None):
        super().__init__()
        self.layout_weight = 1
        self.model = model
        self.autofit = autofit
        self.curr_model = None
        self.columnHeader = columnHeader
        self.rowHeader = rowHeader

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qt_model = prev.qt_model
            self.curr_model = prev.curr_model

            self.ui.clicked.disconnect()
            self.ui.doubleClicked.disconnect()
        else:
            self.qt_model = None
            self.curr_model = Prop()
            self.ui = QtWidgets.QTableView()

        self.ui.clicked.connect(self.on_item_clicked)
        self.ui.doubleClicked.connect(self.on_item_double_clicked)

        if self.model:
            if self.curr_model.set(self.model):
                self.qt_model = QtTableModelAdapter(self)
                self.ui.setModel(self.qt_model)
            else:
                self.qt_model.pui_node = self
                self.qt_model.refresh()
        else:
            self.ui.horizontalHeader().hide()
            self.ui.verticalHeader().hide()
            self.qt_model = QtTableNodeModelAdapter(self)
            self.ui.setModel(self.qt_model)

        if (self.model is None or self.model.columnHeader is None) and self.columnHeader is None:
            self.ui.horizontalHeader().hide()
        else:
            self.ui.horizontalHeader().show()

        if (self.model is None or self.model.rowHeader is None) and self.rowHeader is None:
            self.ui.verticalHeader().hide()
        else:
            self.ui.verticalHeader().show()

        if self.autofit:
            self.ui.resizeColumnsToContents()

        super().update(prev)

    def on_item_clicked(self, index):
        self.get_node().qt_model.clicked(index)

    def on_item_double_clicked(self, index):
        self.get_node().qt_model.dblclicked(index)


class TableNode(PUINode):
    def __init__(self, data=""):
        super().__init__()
        self._set_callback = None
        self.data = data

    def set(self, cb, *args, **kwargs):
        self._set_callback = (cb, args, kwargs)
        return self

    def _set(self, data):
        if self._set_callback:
            cb, args, kwargs = self._set_callback
            cb(data, *args, **kwargs)
