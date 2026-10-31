"""Grid track growth must not stretch compact controls in those tracks."""
import unittest

from PySide6 import QtCore, QtWidgets
from PUI.PySide6 import Grid, Label, Button, TextField, DummyBinding, Window
from PUI.PySide6.base import QtPUIView
from PUI.dom import recur_delete


class GridCellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_compact_weighted_and_spanning_cells_after_redraw(self):
        class View(QtPUIView):
            weight = None
            def content(self):
                with Window(size=(650, 400)):
                    with Grid().layout(weight=1) as self.grid:
                        Label('Tall content').layout(width=120, height=180).grid(row=0, column=0)
                        Button('Connect').id('button').layout(weight=self.weight).grid(row=0, column=1)
                        TextField(DummyBinding('Wide field')).id('field').grid(row=1, column=1)
                        Label('Spanning caption').id('span').grid(row=2, column=0, columnspan=2)
        root = View()
        try:
            button = None
            for weight in (None, 1, 0, None):
                root.weight = weight
                root.sync()
                root.grid.ui.resize(650, 400)
                root.grid.ui.show()
                root.grid.layout.activate()
                self.app.processEvents()
                nodes = {n._id: n for n in root.grid.children}
                widget = nodes['button'].ui
                if button is not None:
                    self.assertIs(widget, button)
                button = widget
                cell = root.grid.layout.cellRect(0, 1)
                item_rect = root.grid.layout.itemAt(root.grid.layout.indexOf(widget)).geometry()
                if weight == 1:
                    self.assertEqual(item_rect, cell)
                else:
                    self.assertEqual(widget.size(), widget.sizeHint())
                    self.assertEqual(widget.x(), cell.x())
                    # Use the layout item to account for Cocoa button margins.
                    self.assertLessEqual(abs(item_rect.center().y()-cell.center().y()), 1)
                field = nodes['field'].ui
                self.assertEqual(field.width(), root.grid.layout.cellRect(1, 1).width())
                self.assertEqual(field.height(), field.sizeHint().height())
                span = nodes['span'].ui
                self.assertEqual(span.size(), span.sizeHint())
                self.assertGreater(cell.width(), widget.sizeHint().width()+100)
        finally:
            recur_delete(root, root, True)
            self.app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
