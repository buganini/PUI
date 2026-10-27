"""Common Canvas color/path/image contract and Matplotlib display-list adapter."""
import unittest
from PUI import Color
from PUI.color import rgba, css_color
from PUI._path import PathOp as O, FillRule as R, path_commands
from PUI._rgba import RGBAImage


class CanvasPathTests(unittest.TestCase):
    def test_trgb_compatibility_and_validation(self):
        self.assertEqual(Color(0x123456),0x123456)
        self.assertEqual(Color(0x123456,.5),0x80123456)
        self.assertEqual(rgba(Color(0x123456,0)),(0x12,0x34,0x56,0))
        self.assertEqual(css_color(Color(0x123456,.5)),'#1234567f')
        for alpha in (-1,2,float('nan'),float('inf')):
            with self.assertRaises(ValueError): Color(0,alpha)
        for value in (-1,0x1000000):
            with self.assertRaises(ValueError): Color(value)

    def test_path_validation_and_subpaths(self):
        path=[(O.MoveTo,0,0),(O.QuadTo,5,10,10,0),(O.CubicTo,15,-10,20,10,25,0),(O.Close,)]
        commands=path_commands(path)
        self.assertEqual(commands[1],('Q',5,10,10,0))
        for bad in ([('M',0,0)],[(O.LineTo,0,0)],[(O.MoveTo,float('nan'),0)],[(O.CubicTo,1,2)]):
            with self.assertRaises(ValueError):path_commands(bad)

    def test_rgba_is_detached_and_png_preserves_pixels(self):
        from PIL import Image
        from io import BytesIO
        data=bytearray([255,0,0,128,0,0,255,255]);im=RGBAImage(1,2,data)
        data[0]=0
        self.assertEqual(Image.open(BytesIO(im.png)).tobytes(),im.data)
        with self.assertRaises(ValueError):RGBAImage(2,2,b'')
        cropped=im.crop(0,1,1,2)
        self.assertEqual(cropped.data,b'\0\0\xff\xff\0\0\0\0')

    def test_browser_recording(self):
        from PUI.web import Canvas
        canvas=object.__new__(Canvas);canvas._commands=[]
        canvas.push();canvas.clipRect(1,2,3,4)
        path=[(O.MoveTo,0,0),(O.LineTo,20,10),(O.Close,)]
        canvas.clipPath(path);canvas.drawPath(path,fill=Color(0xFF0000,.5));canvas.pop()
        canvas.drawImage(canvas.loadRGBA(1,1,b'\xff\0\0\xff'))
        self.assertEqual([c[0] for c in canvas._commands],['push','clipRect','clipPath','vector','pop','rgba'])
        self.assertEqual(canvas._commands[3][3],'#ff00007f')

    def test_matplotlib_curve_text_clip_image_and_resize(self):
        import numpy as np
        from matplotlib.figure import Figure
        from matplotlib.patches import Circle
        from PUI._matplotlib_renderer import FigureCanvasPUI
        from PUI.web import Canvas
        c=object.__new__(Canvas);c._commands=[];c.width=600;c.height=400
        figure=Figure(dpi=100);ax=figure.subplots()
        ax.plot([0,1],[0,1],alpha=.5);ax.set_title(r'$x^2$')
        im=np.zeros((2,2,4));im[0,:,0]=1;im[1,:,2]=1;im[:,:,3]=1
        image=ax.imshow(im,extent=(0,1,0,1));image.set_clip_path(Circle((.5,.5),.5,transform=ax.transData))
        fc=FigureCanvasPUI(figure,c);fc.paint(c)
        kinds=[x[0] for x in c._commands]
        self.assertIn('clipPath',kinds);self.assertIn('rgba',kinds)
        self.assertEqual(kinds.count('push'),kinds.count('pop'))
        self.assertTrue(any(any(op[0] in ('Q','C') for op in cmd[1]) for cmd in c._commands if cmd[0]=='vector'))
        self.assertEqual(tuple(figure.get_size_inches()),(6,4))
        c.width=800;c.height=500;c._commands=[];fc.paint(c)
        self.assertEqual(tuple(figure.get_size_inches()),(8,5))


if __name__=='__main__':unittest.main()
