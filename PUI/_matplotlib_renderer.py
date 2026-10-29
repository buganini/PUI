"""Matplotlib renderer targeting the public PUI Canvas API (no rasterized figure)."""
from contextlib import contextmanager
from matplotlib.backend_bases import RendererBase, FigureCanvasBase
from matplotlib.path import Path
from matplotlib.transforms import Affine2D
from .color import Color
from ._path import PathOp, FillRule


def pui_path(path, transform, height):
    transform = transform + Affine2D().scale(1, -1).translate(0, height)
    operations = {Path.MOVETO:PathOp.MoveTo, Path.LINETO:PathOp.LineTo,
                  Path.CURVE3:PathOp.QuadTo, Path.CURVE4:PathOp.CubicTo, Path.CLOSEPOLY:PathOp.Close}
    return [(operations[code], *([] if code==Path.CLOSEPOLY else vertices.tolist()))
            for vertices,code in path.iter_segments(transform, remove_nans=True, simplify=False, curves=True)
            if code in operations]


def color(value, gc):
    if value is None: return None
    alpha = gc.get_alpha() if gc.get_forced_alpha() else (value[3] if len(value)>3 else 1)
    rgb = [round(max(0,min(1,v))*255) for v in value[:3]]
    return Color((rgb[0]<<16)|(rgb[1]<<8)|rgb[2], alpha)


class RendererPUI(RendererBase):
    def __init__(self, canvas, dpi, size=None):
        super().__init__()
        self.canvas, self.dpi = canvas, dpi
        self.width, self.height = size if size is not None else (canvas.width, canvas.height)

    def points_to_pixels(self, points):
        return float(points*self.dpi/72)

    def get_canvas_width_height(self):
        return self.width,self.height

    def flipy(self):
        return False

    def option_image_nocomposite(self):
        return True

    @contextmanager
    def clipped(self, gc):
        self.canvas.push()
        try:
            rect = gc.get_clip_rectangle()
            if rect is not None:
                x,y,w,h = map(float,rect.bounds)
                self.canvas.clipRect(x,self.height-y-h,w,h)
            path,transform = gc.get_clip_path()
            if path is not None:
                self.canvas.clipPath(pui_path(path,transform,self.height),FillRule.NonZero)
            yield
        finally:
            self.canvas.pop()

    def draw_path(self, gc, path, transform, rgbFace=None):
        with self.clipped(gc):
            self.canvas.drawPath(pui_path(path,transform,self.height),
                fill=color(rgbFace,gc),
                stroke=color(gc.get_rgb(),gc) if gc.get_linewidth()>0 else None,
                width=self.points_to_pixels(gc.get_linewidth()),fillRule=FillRule.NonZero)

    def draw_image(self, gc, x, y, im, transform=None):
        if transform is not None:
            raise NotImplementedError('Affine image rendering is not enabled')
        h,w = im.shape[:2]
        # Matplotlib renderer image rows start at the bottom; PUI starts at top.
        image=self.canvas.loadRGBA(w,h,im[::-1].tobytes())
        with self.clipped(gc):
            self.canvas.drawImage(image,float(x),float(self.height-y-h),opacity=float(gc.get_alpha()))

    def draw_gouraud_triangles(self, gc, triangles_array, colors_array, transform):
        raise NotImplementedError('Gouraud shading is not implemented by RendererPUI')


class FigureCanvasPUI(FigureCanvasBase):
    def __init__(self, figure, owner):
        super().__init__(figure)
        self.owner=owner
        self._painting=False
        self._renderer = None

    def get_renderer(self):
        # Cursor/annotation tools need synchronous text and extent measurements,
        # including before the first asynchronous PUI paint. Drawing still takes
        # place only inside paint(), against its current Canvas command buffer.
        width, height = map(float, self.figure.bbox.size)
        dpi = self.figure.dpi
        if (self._renderer is None or
                (self._renderer.width, self._renderer.height, self._renderer.dpi) != (width, height, dpi)):
            self._renderer = RendererPUI(None, dpi, size=(width, height))
        return self._renderer

    def draw(self):
        if not self._painting and self.owner is not None:
            self.owner.get_node()._request_mpl_draw()

    def draw_idle(self):
        self.draw()

    def paint(self, canvas):
        self._painting=True
        try:
            # PUI uses logical coordinates; the backend applies device density.
            dpi=self.figure.dpi
            self.figure.set_size_inches(canvas.width/dpi,canvas.height/dpi,forward=False)
            renderer = self.get_renderer()
            renderer.canvas = canvas
            try:
                self.figure.draw(renderer)
            finally:
                # Do not retain or append to a completed frame's command buffer.
                renderer.canvas = None
        finally:
            self._painting=False
