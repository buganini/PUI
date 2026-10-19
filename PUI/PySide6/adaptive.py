from PySide6 import QtCore, QtWidgets


def observe(node):
    ui = node.ui
    if isinstance(ui, QtWidgets.QMainWindow):
        ui = ui.centralWidget() or ui

    class ResizeFilter(QtCore.QObject):
        def __init__(self):
            super().__init__(ui)
            self.pending = False

        def schedule(self):
            if not self.pending:
                self.pending = True
                QtCore.QTimer.singleShot(0, self.measure)

        def measure(self):
            self.pending = False
            if node.get_node().destroyed:
                return
            rect = ui.contentsRect()
            layout = ui.layout()
            if layout is not None:
                rect = rect.marginsRemoved(layout.contentsMargins())
            node._set_size(rect.width(), rect.height())

        def eventFilter(self, obj, event):
            if event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Show,
                                QtCore.QEvent.LayoutRequest, QtCore.QEvent.ContentsRectChange):
                self.schedule()
            return False

    listener = ResizeFilter()
    ui.installEventFilter(listener)
    listener.schedule()
    def close():
        # Native destruction also removes the parent-owned filter.
        import shiboken6
        if shiboken6.isValid(ui):
            ui.removeEventFilter(listener)
            listener.deleteLater()
    return close
