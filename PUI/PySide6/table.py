from .. import *
from .base import *

class QtTableModelAdapter(QtCore.QAbstractTableModel):
    def __init__(self, model: "BaseTableAdapter"):
        super().__init__()
        self.model = model

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
                        return None
                    else:
                        return self.model.columnHeader(section)
                else:
                    return super().headerData(section, orientation, role)
            else:
                if hasattr(self.model, "rowHeader"):
                    if self.model.rowHeader is None:
                        return None
                    else:
                        return self.model.rowHeader(section)
                else:
                    return super().headerData(section, orientation, role)

    def rowCount(self, index):
        return self.model.rowCount()

    def columnCount(self, index):
        return self.model.columnCount()


class Table(QtBaseWidget):
    def __init__(self, model, autofit=True):
        super().__init__()
        self.layout_weight = 1
        self.model = model
        self.autofit = autofit
        self.curr_model = None

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qt_model = prev.qt_model
            self.curr_model = prev.curr_model
        else:
            self.qt_model = None
            self.curr_model = Prop()
            self.ui = QtWidgets.QTableView()

        if self.model.columnHeader is None:
            self.ui.horizontalHeader().hide()
        else:
            self.ui.horizontalHeader().show()

        if self.model.rowHeader is None:
            self.ui.verticalHeader().hide()
        else:
            self.ui.verticalHeader().show()

        if self.curr_model.set(self.model):
            self.qt_model = QtTableModelAdapter(self.model)
            self.ui.setModel(self.qt_model)
        else:
            self.qt_model.refresh()

        if self.autofit:
            self.ui.resizeColumnsToContents()

        super().update(prev)
