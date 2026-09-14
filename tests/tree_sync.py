import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from PUI.PySide6.base import QtPUIView
from PUI.PySide6.tree import Tree, TreeNode


class TreeView(QtPUIView):
    def __init__(self):
        self.generation = 0
        super().__init__()

    def content(self):
        with Tree().expandAll():
            with TreeNode(f"root {self.generation}"):
                with TreeNode(f"child {self.generation}"):
                    TreeNode(f"grandchild {self.generation}")


class TreeSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_redraw_remaps_indexes_and_preserves_expansion(self):
        view = TreeView()
        view.sync()

        old_tree = view.children[0]
        old_root_index = old_tree.qt_model.index(0, 0)
        old_child_index = old_tree.qt_model.index(0, 0, old_root_index)
        old_root = old_root_index.internalPointer()
        old_child = old_child_index.internalPointer()
        persistent_child = QtCore.QPersistentModelIndex(old_child_index)

        self.assertTrue(old_tree.ui.isExpanded(old_root_index))
        self.assertTrue(old_tree.ui.isExpanded(old_child_index))

        view.generation = 1
        view.sync()

        new_tree = view.children[0]
        new_root_index = new_tree.qt_model.index(0, 0)
        new_child_index = new_tree.qt_model.index(0, 0, new_root_index)

        self.assertIs(old_root.get_node(), new_root_index.internalPointer())
        self.assertIs(old_child.get_node(), new_child_index.internalPointer())
        self.assertIs(persistent_child.internalPointer(), new_child_index.internalPointer())
        self.assertTrue(new_tree.ui.isExpanded(new_root_index))
        self.assertTrue(new_tree.ui.isExpanded(new_child_index))
        self.assertEqual(
            new_tree.qt_model.data(new_child_index, QtCore.Qt.DisplayRole),
            "child 1",
        )


if __name__ == "__main__":
    unittest.main()
