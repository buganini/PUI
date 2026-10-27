"""Matplotlib's native Agg canvas embedded in PUI."""
from .base import WxBaseWidget, getWindow, wx


class MatplotlibCanvas(WxBaseWidget):
    expand_x_prio = 4
    expand_y_prio = 4

    def __init__(self, plotter, *args, **kwargs):
        super().__init__()
        self.plotter, self.args, self.kwargs = plotter, args, kwargs
        self.figure = self.figure_canvas = None

    def update(self, prev):
        from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
        from matplotlib.figure import Figure
        if prev is not None and prev.ui is not None:
            self.figure, self.figure_canvas, self.ui = prev.figure, prev.figure_canvas, prev.ui
        else:
            self.figure = Figure()
            self.figure_canvas = FigureCanvasWxAgg(getWindow(self.parent), -1, self.figure)
            self.ui = self.figure_canvas
            self.ui.Bind(wx.EVT_WINDOW_DESTROY, _release_capture_on_destroy)
        self.plotter(self.figure, *self.args, **self.kwargs)
        super().update(prev)
        self.figure_canvas.draw_idle()

    def releaseRetiredRefs(self):
        self.figure = self.figure_canvas = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        if self.ui is not None and self.ui and self.ui.HasCapture():
            self.ui.ReleaseMouse()
        self.figure = self.figure_canvas = None
        super().destroy(direct)


def _release_capture_on_destroy(event):
    # Parent-window teardown can bypass the child node's destroy().
    widget = event.GetEventObject()
    if widget.HasCapture():
        widget.ReleaseMouse()
    event.Skip()
