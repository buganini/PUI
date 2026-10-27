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
        self._connect_mpl_events()
        super().update(prev)

    def _connect_mpl_events(self):
        from ._matplotlib_events import MatplotlibEvents
        if not hasattr(self.figure_canvas, 'input_events'):
            self.figure_canvas.input_events = MatplotlibEvents(self.figure_canvas)
        for attr, name in (
            ('_onMouseDown', 'button_press_event'), ('_onMouseUp', 'button_release_event'),
            ('_onMouseMove', 'motion_notify_event'), ('_onMouseEnter', 'figure_enter_event'),
            ('_onMouseLeave', 'figure_leave_event'), ('_onWheel', 'scroll_event')):
            previous = getattr(self, attr)
            if previous and getattr(previous[0], '_mpl_forward', False):
                continue
            def forward(event, name=name, previous=previous):
                node = self.get_node()
                if node.destroyed or node.figure_canvas is None:
                    return
                node.figure_canvas.input_events.pointer(name, event)
                if previous:
                    callback, args, kwargs = previous
                    callback(event, *args, **kwargs)
            forward._mpl_forward = True
            setattr(self, attr, (forward, (), {}))
        self._onMplKeyDown = (self._mpl_keydown, (), {})
        self._onMplKeyUp = (self._mpl_keyup, (), {})
        self._onMplBlur = (self._mpl_blur, (), {})

    @property
    def pointer_handlers(self):
        return {**super().pointer_handlers,
                'keydown': ('_onMplKeyDown', '_mpl_keydown'),
                'keyup': ('_onMplKeyUp', '_mpl_keyup'),
                'blur': ('_onMplBlur', '_mpl_blur')}

    def _mpl_keydown(self, event):
        self.figure_canvas.input_events.key('key_press_event', event)

    def _mpl_keyup(self, event):
        self.figure_canvas.input_events.key('key_release_event', event)

    def _mpl_blur(self, event=None):
        if self.figure_canvas is not None:
            self.figure_canvas.input_events.reset()

    def reset_connection(self):
        self._mpl_blur()
        super().reset_connection()

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
