import os
import sys
import unittest

sys.modules["jurigged"] = None

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from PUI.PySide6.base import QtPUIView
from PUI.PySide6.table import Table, TableNode


class RaggedRowsView(QtPUIView):
    def __init__(self, first_row, second_row, **table_options):
        self.first_row = first_row
        self.second_row = second_row
        self.table_options = table_options
        super().__init__()

    def content(self):
        with Table(**self.table_options):
            with TableNode():
                for value in self.first_row:
                    TableNode(value)
            with TableNode():
                for value in self.second_row:
                    TableNode(value)


class EmptyTableView(QtPUIView):
    def __init__(self, **table_options):
        self.table_options = table_options
        super().__init__()

    def content(self):
        Table(**self.table_options)


class TableRaggedRowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_uses_widest_row_when_later_row_is_longer(self):
        view = RaggedRowsView(["A1", "A2"], ["B1", "B2", "B3"])
        view.sync()
        model = view.children[0].qt_model

        self.assertEqual(model.rowCount(QtCore.QModelIndex()), 2)
        self.assertEqual(model.columnCount(QtCore.QModelIndex()), 3)
        self.assertEqual(
            model.data(model.index(1, 2), QtCore.Qt.DisplayRole),
            "B3",
        )

    def test_missing_cell_is_empty_and_inert(self):
        view = RaggedRowsView(["A1", "A2", "A3"], ["B1", "B2"])
        view.sync()
        model = view.children[0].qt_model
        missing = model.index(1, 2)

        self.assertTrue(missing.isValid())
        self.assertIsNone(model.data(missing, QtCore.Qt.DisplayRole))
        self.assertEqual(model.flags(missing), QtCore.Qt.ItemFlag.NoItemFlags)
        self.assertFalse(model.setData(missing, "value", QtCore.Qt.EditRole))
        model.clicked(missing)
        model.dblclicked(missing)

    def test_explicit_counts_create_empty_rows_and_columns(self):
        view = RaggedRowsView(
            ["A1"],
            [],
            rowCount=4,
            columnCount=5,
            rowHeader=["First"],
            columnHeader=["Value"],
        )
        view.sync()
        model = view.children[0].qt_model

        self.assertEqual(model.rowCount(QtCore.QModelIndex()), 4)
        self.assertEqual(model.columnCount(QtCore.QModelIndex()), 5)
        self.assertIsNone(
            model.data(model.index(3, 4), QtCore.Qt.DisplayRole)
        )
        self.assertIsNone(
            model.headerData(4, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
        )
        self.assertIsNone(
            model.headerData(3, QtCore.Qt.Vertical, QtCore.Qt.DisplayRole)
        )

    def test_headers_define_automatic_counts_for_empty_table(self):
        view = EmptyTableView(
            rowHeader=["R1", "R2"],
            columnHeader=["C1", "C2", "C3"],
        )
        view.sync()
        model = view.children[0].qt_model

        self.assertEqual(model.rowCount(QtCore.QModelIndex()), 2)
        self.assertEqual(model.columnCount(QtCore.QModelIndex()), 3)
        self.assertIsNone(
            model.data(model.index(1, 2), QtCore.Qt.DisplayRole)
        )

    def test_counts_must_be_non_negative_integers(self):
        with self.assertRaises(ValueError):
            Table(columnCount=-1)
        with self.assertRaises(ValueError):
            Table(rowCount=1.5)
        with self.assertRaises(ValueError):
            Table(rowCount=True)


if __name__ == "__main__":
    unittest.main()
