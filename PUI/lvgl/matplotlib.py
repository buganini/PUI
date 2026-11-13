"""Matplotlib figures rendered through the shared PUI Canvas renderer."""
from .._matplotlib import MatplotlibMixin
from .canvas import Canvas


class MatplotlibCanvas(MatplotlibMixin, Canvas):
    def _request_mpl_draw(self):
        if not self.destroyed and self.ui is not None:
            self._request_paint()
