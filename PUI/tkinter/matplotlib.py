"""Matplotlib's native Agg canvas embedded in PUI."""
from .base import TkBaseWidget, tk


class MatplotlibCanvas(TkBaseWidget):
    expand_x_prio = 4
    expand_y_prio = 4

    def __init__(self, plotter, *args, **kwargs):
        super().__init__()
        self.plotter, self.args, self.kwargs = plotter, args, kwargs
        self.figure = self.figure_canvas = None

    def update(self, prev):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        if prev is not None and prev.ui is not None:
            self.figure, self.figure_canvas, self.ui = prev.figure, prev.figure_canvas, prev.ui
        else:
            self.figure = Figure()
            self.figure_canvas = FigureCanvasTkAgg(self.figure, master=self.tkparent.inner)
            self.ui = self.figure_canvas.get_tk_widget()
        self.plotter(self.figure, *self.args, **self.kwargs)
        super().update(prev)
        self.figure_canvas.draw_idle()

    def releaseRetiredRefs(self):
        self.figure = self.figure_canvas = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        # Embedded canvases have no FigureManagerTk to cancel pending work.
        if self.figure_canvas is not None:
            for name in ('_idle_draw_id', '_event_loop_id'):
                timer = getattr(self.figure_canvas, name, None)
                if timer is not None:
                    try:
                        self.ui.after_cancel(timer)
                    except tk.TclError:
                        pass  # The containing native window may already be gone.
                    setattr(self.figure_canvas, name, None)
        self.figure = self.figure_canvas = None
        super().destroy(direct)
