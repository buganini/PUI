from .. import *
from .base import *

class QtTableModelAdapter(QtCore.QAbstractTableModel):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            return self.model.data(index.row(), index.column())

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if hasattr(self.model, "columnHeader"):
                    return self.model.columnHeader(section)
                else:
                    return super().headerData(section, orientation, role)
            else:
                if hasattr(self.model, "rowHeader"):
                    return self.model.rowHeader(section)
                else:
                    return super().headerData(section, orientation, role)

    def rowCount(self, index):
        return self.model.rowCount()

    def columnCount(self, index):
        return self.model.columnCount()


class Table(QtBaseWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.last_model = None

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QTableView()

        print(self.last_model, self.model, self.last_model != self.model)
        if self.last_model != self.model:
            self.ui.setModel(QtTableModelAdapter(self.model))
            self.last_model = self.model

        super().update(prev)
