"""Run each toolkit separately: PUI_TEST_BACKEND=wx PYTHONPATH=tests:. python -m unittest canvas_paths_native."""
import importlib
import os
import unittest
from PUI import Color
from PUI._path import PathOp as O, FillRule as R


class NativePaths(unittest.TestCase):
    def test_paths_clipping_memory_image_and_matplotlib(self):
        name=os.environ.get('PUI_TEST_BACKEND','PySide6')
        UI=importlib.import_module('PUI.'+name)
        c=UI.Canvas(lambda c:None);c.width=800;c.height=600
        if name=='PySide6':
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QImage,QPainter
            app=QApplication.instance() or QApplication([])
            image=QImage(800,600,QImage.Format_ARGB32_Premultiplied);image.fill(0xFFFFFFFF)
            painter=QPainter(image);c._begin_paint(painter)
            self.addCleanup(lambda image=image: None)
            self.addCleanup(c._end_paint);self.addCleanup(painter.end)
        elif name=='wx':
            import wx
            app=wx.GetApp() or wx.App()
            bitmap=wx.Bitmap(800,600);c.dc=wx.MemoryDC(bitmap)
            c.dc.SetBackground(wx.Brush('white'));c.dc.Clear()
            self.addCleanup(c.dc.SelectObject,wx.NullBitmap)
        elif name=='tkinter':
            import tkinter as tk
            root=tk.Tk();root.withdraw();self.addCleanup(root.destroy)
            c.ui=tk.Canvas(root,width=800,height=600)
        else:
            import flet.canvas as cv
            c.ui=cv.Canvas()
        outer=[(O.MoveTo,10,10),(O.LineTo,110,10),(O.LineTo,110,110),(O.LineTo,10,110),(O.Close,)]
        inner=[(O.MoveTo,35,35),(O.LineTo,85,35),(O.LineTo,85,85),(O.LineTo,35,85),(O.Close,)]
        if name == 'tkinter':
            with self.assertRaises(NotImplementedError): c.drawPath(outer+inner,fill=0)
            c.drawPath(outer+inner,stroke=0)
        elif name == 'flet':
            with self.assertRaises(NotImplementedError): c.drawPath(outer+inner,fill=0,fillRule=R.EvenOdd)
            c.drawPath(outer+inner,fill=Color(0xFF0000,.5))
        else:
            c.drawPath(outer+inner,fill=Color(0xFF0000,.5),fillRule=R.EvenOdd)
        c.push();c.clipRect(150,10,30,30)
        if name != 'tkinter': c.drawPath([(O.MoveTo,130,0),(O.LineTo,200,0),(O.LineTo,200,80),(O.LineTo,130,80),(O.Close,)],fill=0)
        c.pop()
        if name=='PySide6':
            self.assertGreater(image.pixelColor(20,20).green(),120)
            self.assertEqual(image.pixelColor(50,50).name(),'#ffffff')
            self.assertEqual(image.pixelColor(160,20).name(),'#000000')
            self.assertEqual(image.pixelColor(140,20).name(),'#ffffff')
        if name=='wx':
            with self.assertRaises(NotImplementedError):c.clipPath(outer)
        else:c.push();c.clipPath(outer);c.pop()
        c.drawImage(c.loadRGBA(1,2,b'\xff\0\0\xff\0\0\xff\xff'),220,10,20,40)
        if name == 'tkinter':
            with self.assertRaises(NotImplementedError): c.drawPath([(O.MoveTo,0,0),(O.QuadTo,10,10,20,0)])
            return
        from matplotlib.figure import Figure
        from PUI._matplotlib_renderer import FigureCanvasPUI
        f=Figure();ax=f.subplots();ax.plot([0,1],[0,1]);ax.set_title(r'$x^2$')
        FigureCanvasPUI(f,c).paint(c)
        # Exercise the six-panel cookbook without importing its backend config.
        os.environ['PUI_BACKEND']=name
        module=importlib.import_module('PUI.cookbook.matplotlib')
        module.MatplotlibCanvasExample.plot(f)
        if name == 'wx':
            # The cookbook now uses native WxAgg; the ordinary wx Canvas still
            # cannot clip images to arbitrary paths.
            f.axes[4].images[0].set_clip_path(None)
        FigureCanvasPUI(f,c).paint(c)
        if name=='flet':
            self.assertGreater(len(c.ui.shapes),100)
