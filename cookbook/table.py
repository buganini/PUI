from .config import *

class TableExample(PUIView):
    class TableAdapter(BaseTableAdapter):
        def __init__(self, data):
            self._data = data

        def data(self, row, col):
            return self._data.value[row][col]

        # def editData(self, row, col):
        #     return f"V{self._data.value[row][col]}"

        def setData(self, row, col, value):
            self._data.value[row][col] = value
            self._data.emit()

        def editable(self, row, col):
            if row < 3:
                return True
            return False

        def columnHeader(self, col):
            return f"Col {col}"

        rowHeader = None

        def rowCount(self):
            return len(self._data.value)

        def columnCount(self):
            return len(self._data.value[0])

    def setup(self):
        self.state = State()
        self.state.data = [
            [4, 9, 2],
            [1, 0, 0],
            [3, 5, 0],
            [3, 3, 2],
            [7, 8, 9],
        ]

    def content(self):
        with VBox():
            Table(self.TableAdapter(self.state("data")))
            Table(self.TableAdapter(self.state("data")))
