import os
import sys
import unittest

sys.modules["jurigged"] = None

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from PUI import State
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


class TableNodeOptionsView(QtPUIView):
    def __init__(self):
        self.state = State()
        self.state.value = 2
        self.state.direction = "CW"
        self.updated = None
        super().__init__()

    def content(self):
        with Table():
            with TableNode():
                TableNode("Readonly")
                TableNode(
                    self.state("value"),
                    display=f"Value: {self.state.value}",
                )
                TableNode(
                    self.state("direction"),
                    choices={
                        "CW": "Clockwise",
                        "CCW": "Counterclockwise",
                    },
                )
                TableNode(
                    self.state("direction"),
                    display=f"Direction: {self.state.direction}",
                    choices=("CCW", "CW"),
                )
                TableNode(
                    "unknown",
                    choices={"CW": "Clockwise"},
                ).set(self.on_set)
                TableNode(
                    1,
                    choices=(1, 2, 3),
                ).set(self.on_set)
                TableNode("Fallback", display=None)

    def on_set(self, value):
        self.updated = value


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

    def test_display_and_choices_keep_edit_data_separate(self):
        view = TableNodeOptionsView()
        view.sync()
        model = view.children[0].qt_model

        self.assertEqual(
            model.data(model.index(0, 1), QtCore.Qt.DisplayRole),
            "Value: 2",
        )
        self.assertEqual(
            model.data(model.index(0, 1), QtCore.Qt.EditRole),
            2,
        )
        self.assertEqual(
            model.data(model.index(0, 2), QtCore.Qt.DisplayRole),
            "Clockwise",
        )
        self.assertEqual(
            model.data(model.index(0, 2), QtCore.Qt.EditRole),
            "CW",
        )
        self.assertEqual(
            model.data(model.index(0, 3), QtCore.Qt.DisplayRole),
            "Direction: CW",
        )
        self.assertEqual(
            model.data(model.index(0, 6), QtCore.Qt.DisplayRole),
            "Fallback",
        )

    def test_choices_do_not_make_readonly_data_editable(self):
        view = TableNodeOptionsView()
        view.sync()
        model = view.children[0].qt_model

        self.assertFalse(
            model.flags(model.index(0, 0)) & QtCore.Qt.ItemIsEditable
        )
        self.assertTrue(
            model.flags(model.index(0, 4)) & QtCore.Qt.ItemIsEditable
        )

    def test_mapping_choice_editor_uses_labels_and_raw_values(self):
        view = TableNodeOptionsView()
        view.sync()
        table = view.children[0]
        index = table.qt_model.index(0, 2)
        editor = table.delegate.createEditor(
            table.ui,
            QtWidgets.QStyleOptionViewItem(),
            index,
        )
        table.delegate.setEditorData(editor, index)

        self.assertIsInstance(editor, QtWidgets.QComboBox)
        self.assertEqual(editor.itemText(0), "Clockwise")
        self.assertEqual(editor.itemData(0), "CW")
        self.assertEqual(editor.currentData(), "CW")
        self.assertEqual(
            editor.backgroundRole(),
            QtGui.QPalette.ColorRole.Base,
        )
        self.assertTrue(editor.autoFillBackground())

    def test_sequence_choice_editor_preserves_value_type(self):
        view = TableNodeOptionsView()
        view.sync()
        table = view.children[0]
        index = table.qt_model.index(0, 5)
        editor = table.delegate.createEditor(
            table.ui,
            QtWidgets.QStyleOptionViewItem(),
            index,
        )
        table.delegate.setEditorData(editor, index)
        editor.setCurrentIndex(1)
        table.delegate.setModelData(editor, table.qt_model, index)

        self.assertEqual(view.updated, 2)
        self.assertIsInstance(view.updated, int)

    def test_choice_selection_commits_without_waiting_for_blur(self):
        view = TableNodeOptionsView()
        view.sync()
        table = view.children[0]
        index = table.qt_model.index(0, 5)
        table.ui.show()
        table.ui.edit(index)
        self.app.processEvents()
        editor = table.ui.findChild(QtWidgets.QComboBox)

        self.assertIsNotNone(editor)
        editor.setCurrentIndex(1)
        editor.activated.emit(1)

        self.assertEqual(view.updated, 2)

    def test_unknown_choice_uses_placeholder(self):
        view = TableNodeOptionsView()
        view.sync()
        table = view.children[0]
        index = table.qt_model.index(0, 4)
        editor = table.delegate.createEditor(
            table.ui,
            QtWidgets.QStyleOptionViewItem(),
            index,
        )
        table.delegate.setEditorData(editor, index)

        self.assertEqual(editor.currentIndex(), -1)
        self.assertEqual(editor.placeholderText(), "unknown")

    def test_choices_must_be_a_mapping_or_sequence(self):
        with self.assertRaises(TypeError):
            TableNode("value", choices="abc")
        with self.assertRaises(TypeError):
            TableNode("value", choices={1, 2, 3})


if __name__ == "__main__":
    unittest.main()
