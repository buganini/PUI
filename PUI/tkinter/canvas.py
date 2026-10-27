from __future__ import annotations
from ..color import rgb_color
from .. import _typing as _t
from .._canvas import CanvasScope
from .. import *
from .base import *
import itertools
class Canvas(CanvasScope, TkBaseWidget):
    pui_terminal = True
    expand_x_prio = 4
    expand_y_prio = 4

    def __init__(self, painter: _t.Callback, *args: _t.Any) -> None:
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
        return (rgb_color(self.style_color) if self.style_color is not None else
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
        node._image_refs = []
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
            self._paint_colors[color] = rgb_color(color)
        return self._paint_colors[color]

    def drawText(
        self,
        x: _t.Number,
        y: _t.Number,
        text: _t.Any,
        w: _t.Number | None = None,
        h: _t.Number | None = None,
        size: _t.Number = 12,
        color: int | None = None,
        rotate: _t.Number = 0,
        anchor: Anchor = Anchor.LeftTop,
    ) -> None:
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

    def drawLine(
        self,
        x1: _t.Number,
        y1: _t.Number,
        x2: _t.Number,
        y2: _t.Number,
        color: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        if color is None:
            return
        params = {'fill': self._color(color)}
        if not width is None:
            params["width"] = width
        self.ui.create_line(x1, y1, x2, y2, **params)

    def drawPolyline(self, coords: _t.Points, color: int | None = None, width: _t.Number = 1) -> None:
        if color is None or len(coords) < 2:
            return
        params = {'fill': self._color(color)}
        if not width is None:
            params["width"] = width
        self.ui.create_line(*itertools.chain(*coords), **params)

    def drawPolygon(
        self,
        coords: _t.Points,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        if len(coords) < 3:
            return
        self.ui.create_polygon(*itertools.chain.from_iterable(coords),
                               fill=self._color(fill), outline=self._color(stroke), width=width)

    def drawRect(
        self,
        x1: _t.Number,
        y1: _t.Number,
        x2: _t.Number,
        y2: _t.Number,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        self.ui.create_rectangle(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2),
                                 fill=self._color(fill), outline=self._color(stroke), width=width)

    def drawEllipse(
        self,
        x: _t.Number,
        y: _t.Number,
        rx: _t.Number,
        ry: _t.Number,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        self.ui.create_oval(x - rx, y - ry, x + rx, y + ry,
                            fill=self._color(fill), outline=self._color(stroke), width=width)

    def drawPath(self, path, fill=None, stroke=None, width=1, fillRule=CanvasScope.FillRule.NonZero):
        from .._path import path_commands, fill_rule
        commands = path_commands(path)
        fill_rule(fillRule)
        if any(c[0] in ('Q', 'C') for c in commands):
            raise NotImplementedError('Tk Canvas does not support exact quadratic/cubic paths')
        contours, points = [], []
        for op, *values in commands:
            if op == 'M':
                if points: contours.append((points,False))
                points=[tuple(values)]
            elif op == 'L': points.append(tuple(values))
            else:
                contours.append((points,True));points=[points[0]]
        if len(points)>1: contours.append((points,False))
        if fill is not None:
            raise NotImplementedError('Tk Canvas does not expose the requested compound path fill rules; use drawPolygon for native polygons')
        for points,closed in contours:
            if closed: points = points + points[:1]
            self.drawPolyline(points,stroke,width)

    def drawImage(self, image, x=0, y=0, width=None, height=None,
                  src_x=0, src_y=0, src_width=None, src_height=None, opacity=1):
        from .._rgba import RGBAImage
        if not isinstance(image, RGBAImage):
            raise TypeError('Tk Canvas.drawImage currently accepts loadRGBA resources')
        # Pillow provides arbitrary image resampling; native Tk PhotoImage only
        # supports integer zoom/subsample factors. Imported only when needed.
        from PIL import Image, ImageTk
        source=Image.frombytes('RGBA',(image.width,image.height),image.data)
        sw=image.width-src_x if src_width is None else src_width
        sh=image.height-src_y if src_height is None else src_height
        source=source.crop((int(src_x),int(src_y),int(src_x+sw),int(src_y+sh)))
        target=(max(1,round(sw if width is None else width)),max(1,round(sh if height is None else height)))
        if source.size!=target: source=source.resize(target,Image.Resampling.BILINEAR)
        if opacity!=1: source.putalpha(source.getchannel('A').point(lambda a: round(a*max(0,min(1,opacity)))))
        native=ImageTk.PhotoImage(source,master=self.ui)
        if not hasattr(self,'_image_refs'): self._image_refs=[]
        self._image_refs.append(native)
        self.ui.create_image(x,y,image=native,anchor='nw')
