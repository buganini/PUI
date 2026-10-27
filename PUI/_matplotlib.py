"""Lazy optional Matplotlib integration shared by graphical Canvas backends."""


class MatplotlibMixin:
    def __init__(self, plotter, *args, **kwargs):
        self.plotter, self.plot_args, self.plot_kwargs = plotter, args, kwargs
        self.figure = self.figure_canvas = None
        super().__init__(self._paint_mpl)

    def update(self, prev):
        from matplotlib.figure import Figure
        from ._matplotlib_renderer import FigureCanvasPUI
        if prev is not None:
            self.figure, self.figure_canvas = prev.figure, prev.figure_canvas
        if self.figure is None:
            self.figure=Figure()
            self.figure_canvas=FigureCanvasPUI(self.figure,self)
        self.figure_canvas.owner=self
        self.plotter(self.figure,*self.plot_args,**self.plot_kwargs)
        super().update(prev)

    def _paint_mpl(self, canvas):
        if self.figure_canvas is not None:
            self.figure_canvas.paint(canvas)

    def _request_mpl_draw(self):
        if self.destroyed or self.ui is None: return
        if hasattr(self,'drawing'):
            self.drawing.dirty=True
            self.runtime.wake()
        elif hasattr(self.ui,'Refresh'):
            self.ui.Refresh()
        elif hasattr(self.ui,'after_idle'):
            if not getattr(self,'_mpl_pending',False):
                self._mpl_pending=True
                self.ui.after_idle(self._idle_mpl)
        elif hasattr(self,'paint'):
            # Flet runs on its application loop. Coalesce requests there.
            from .flet.base import FView
            app=FView.application(self)
            if app is not None and app.ready and not getattr(self,'_mpl_pending',False):
                self._mpl_pending=True
                app.loop.call_soon(self._idle_mpl,context=app.context.copy())
        else:
            self.ui.update()

    def _idle_mpl(self):
        self._mpl_pending=False
        node=self.get_node()
        if not node.destroyed: node.paint()

    def releaseRetiredRefs(self):
        self.figure=self.figure_canvas=None
        super().releaseRetiredRefs()

    def destroy(self,direct):
        if self.figure_canvas is not None: self.figure_canvas.owner=None
        self.figure=self.figure_canvas=None
        super().destroy(direct)
