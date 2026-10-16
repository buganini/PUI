from .. import *
from .base import *
import itertools
class Canvas(TkBaseWidget):
    pui_terminal = True
    expand_x_prio = 3
    expand_y_prio = 3

    def __init__(self, painter, *args):
        super().__init__()
        self.painter = painter
        self.args = args
        self.pixel_density = 1.0
        self._paint_colors = {}
        self._paint_font = None
        self._paint_text_color = None

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else tk.Canvas(self.tkparent.inner, highlightthickness=0, borderwidth=0)
        if not hasattr(self.ui, '_pui_resize_binding'):
            self.ui._pui_resize_binding = self.ui.bind(
                '<Configure>', lambda event: event.widget.pui_node.paint(), add='+')
        super().update(prev)
        self.paint()

    def _text_color(self):
        return (f'#{self.style_color:06X}' if self.style_color is not None else
                ttk.Style(self.ui).lookup('TLabel', 'foreground') or 'black')

    def _apply_tk_colors(self):
        super()._apply_tk_colors()
        self.ui.itemconfigure('pui_theme_text', fill=self._text_color())

    def paint(self):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        node.width = node.ui.winfo_width() if node.ui.winfo_width() > 1 else node.ui.winfo_reqwidth()
        node.height = node.ui.winfo_height() if node.ui.winfo_height() > 1 else node.ui.winfo_reqheight()
        node.ui.delete('all')
        node._clear_paint_styles()
        try:
            node.painter(node, *node.args)
        finally:
            node._clear_paint_styles()

    def _clear_paint_styles(self):
        self._paint_colors.clear()
        self._paint_font = self._paint_text_color = None

    def _color(self, color):
        if color is None:
            return ''
        if color not in self._paint_colors:
            self._paint_colors[color] = f'#{color:06X}'
        return self._paint_colors[color]

    def drawText(self, x, y, text, w=None, h=None, size=12, color=None, rotate=0, anchor=Anchor.LEFT_TOP):
        vertical = {'top': 'n', 'center': '', 'bottom': 's'}[anchor.value[1]]
        horizontal = {'left': 'w', 'center': '', 'right': 'e'}[anchor.value[0]]
        if self._paint_font is None:
            self._paint_font = tkFont.nametofont('TkDefaultFont', root=self.ui).actual()
        font = self._paint_font
        params = {'anchor': vertical + horizontal or 'center', 'angle': -rotate,
                  'font': (font['family'], size if size is not None else font['size'])}
        if color is None:
            if self._paint_text_color is None:
                self._paint_text_color = self._text_color()
            params['fill'] = self._paint_text_color
            params['tags'] = ('pui_theme_text',)
        else:
            params['fill'] = self._color(color)
        if w is not None:
            params['width'] = w
        self.ui.create_text(x, y, text=text, **params)

    def drawLine(self, x1, y1, x2, y2, color=None, width=1):
        if color is None:
            return
        params = {'fill': self._color(color)}
        if not width is None:
            params["width"] = width
        self.ui.create_line(x1, y1, x2, y2, **params)

    def drawPolyline(self, coords, color=None, width=1):
        if color is None or len(coords) < 2:
            return
        params = {'fill': self._color(color)}
        if not width is None:
            params["width"] = width
        self.ui.create_line(*itertools.chain(*coords), **params)

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        if len(coords) < 3:
            return
        self.ui.create_polygon(*itertools.chain.from_iterable(coords),
                               fill=self._color(fill), outline=self._color(stroke), width=width)

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        self.ui.create_rectangle(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2),
                                 fill=self._color(fill), outline=self._color(stroke), width=width)

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        self.ui.create_oval(x - rx, y - ry, x + rx, y + ry,
                            fill=self._color(fill), outline=self._color(stroke), width=width)
