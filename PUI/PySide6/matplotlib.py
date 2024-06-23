from .base import *

class MatplotlibCanvas(QtBaseWidget):
    def __init__(self, plotter, *args, **kwargs):
        super().__init__()
        self.plotter = plotter
        self.args = args
        self.kwargs = kwargs

    def update(self, prev):
        from matplotlib.backends.backend_qtagg import FigureCanvas
        from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
        from matplotlib.backends.qt_compat import QtWidgets
        from matplotlib.figure import Figure
        if prev and prev.ui:
            self.figure = prev.figure
            self.ui = prev.ui
        else:
            self.figure = Figure()
            self.ui = FigureCanvas(self.figure)
        self.plotter(self.figure, *self.args, **self.kwargs)
        self.ui.draw()
        super().update(prev)
