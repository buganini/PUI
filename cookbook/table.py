from .config import *

class TableExample(PUIView):
    class TableAdapter:
        def __init__(self, data):
            self._data = data

        def data(self, row, col):
            return self._data.value[row][col]

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
        Table(self.TableAdapter(self.state("data")))
