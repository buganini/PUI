from .. import *
from .base import *

class QtTableModelAdapter(QtCore.QAbstractTableModel):
    def __init__(self, node):
        super().__init__()
        self.node = node

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            return self.node.model.data(index.row(), index.column())
        elif role == QtCore.Qt.EditRole:
            if hasattr(self.node.model, "editData"):
                return self.node.model.editData(index.row(), index.column())
            else:
                return self.node.model.data(index.row(), index.column())

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            self.node.model.setData(index.row(), index.column(), value)
            return True

    def flags(self, index):
        flags = super().flags(index)
        if self.node.model.editable(index.row(), index.column()):
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if hasattr(self.node.model, "columnHeader"):
                    if self.node.model.columnHeader is None:
                        return self.node.ui.horizontalHeader().hide()
                    else:
                        return self.node.model.columnHeader(section)
                else:
                    return super().headerData(section, orientation, role)
            else:
                if hasattr(self.node.model, "rowHeader"):
                    if self.node.model.rowHeader is None:
                        return self.node.ui.verticalHeader().hide()
                    else:
                        return self.node.model.rowHeader(section)
                else:
                    return super().headerData(section, orientation, role)

    def rowCount(self, index):
        return self.node.model.rowCount()

    def columnCount(self, index):
        return self.node.model.columnCount()


class Table(QtBaseWidget):
    def __init__(self, model, autofit=True):
        super().__init__()
        self.model = model
        self.autofit = autofit

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qt_model.node = self
        else:
            self.ui = QtWidgets.QTableView()
            self.qt_model = QtTableModelAdapter(self)

        self.ui.setModel(self.qt_model)
        if self.autofit:
            self.ui.resizeColumnsToContents()

        super().update(prev)
