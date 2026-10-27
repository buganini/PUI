"""Pixel-level Canvas text contract. Run Qt and wx in separate processes."""
import os
import unittest
from PIL import Image, ImageChops
from PUI import Anchor, Color


class CanvasTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = os.environ.get('PUI_TEST_BACKEND', 'PySide6')
        if cls.backend == 'PySide6':
            from PySide6.QtWidgets import QApplication
            cls.app = QApplication.instance() or QApplication([])
        else:
            import wx
            cls.app = wx.GetApp() or wx.App()

    def render(self, draw):
        if self.backend == 'PySide6':
            from PUI.PySide6.canvas import Canvas
            from PySide6.QtGui import QImage, QPainter
            from PySide6.QtWidgets import QWidget
            c = Canvas(lambda c: None)
            c.ui = QWidget()
            image = QImage(320, 240, QImage.Format_RGB888)
            image.fill(0xFFFFFF)
            painter = QPainter(image)
            c._begin_paint(painter)
            try:
                draw(c)
            finally:
                painter.end()
                c._end_paint()
                c.ui.close()
            return Image.frombytes('RGB', (320,240), bytes(image.constBits()))
        import wx
        from PUI.wx.canvas import Canvas
        window = wx.Frame(None)
        c = Canvas(lambda c: None)
        c.ui = wx.Panel(window)
        bitmap = wx.Bitmap(320,240)
        c.dc = wx.MemoryDC(bitmap)
        c.dc.SetBackground(wx.Brush('white')); c.dc.Clear()
        try:
            draw(c)
        finally:
            c.dc.SelectObject(wx.NullBitmap)
            window.Destroy()
            self.app.Yield()
        return Image.frombytes('RGB',(320,240),bytes(bitmap.ConvertToImage().GetData()))

    def bbox(self, image):
        return ImageChops.difference(image, Image.new('RGB',image.size,'white')).getbbox()

    def test_all_anchors_position_the_natural_text_block(self):
        boxes = {}
        for anchor in Anchor:
            image = self.render(lambda c: c.drawText(160,120,'MgMg',size=24,color=0,anchor=anchor))
            boxes[anchor.value] = self.bbox(image)
        for vertical in ('top','center','bottom'):
            left,center,right = [boxes[(horizontal,vertical)] for horizontal in ('left','center','right')]
            shift=left[0]-right[0]
            self.assertGreater(shift,30)
            self.assertAlmostEqual(left[0]-center[0],shift/2,delta=2)
            self.assertAlmostEqual(left[1],right[1],delta=1)
        for horizontal in ('left','center','right'):
            top,center,bottom = [boxes[(horizontal,vertical)] for vertical in ('top','center','bottom')]
            shift=top[1]-bottom[1]
            self.assertGreater(shift,20)
            self.assertAlmostEqual(top[1]-center[1],shift/2,delta=2)

    def test_bounds_clip_in_rotated_text_coordinates(self):
        for rotation in (0,90):
            im=self.render(lambda c:c.drawText(120,100,'MMMMMMMM\nMMMMMMMM',size=24,color=0,
                                               w=30,h=25,rotate=rotation))
            box=self.bbox(im)
            self.assertIsNotNone(box)
            if rotation==0:
                self.assertGreaterEqual(box[0],120);self.assertLessEqual(box[2],150)
                self.assertGreaterEqual(box[1],100);self.assertLessEqual(box[3],125)
            else:
                self.assertGreaterEqual(box[0],94);self.assertLessEqual(box[2],121)
                self.assertGreaterEqual(box[1],100);self.assertLessEqual(box[3],131)

    def test_font_size_multiline_and_zero_bounds(self):
        small=self.bbox(self.render(lambda c:c.drawText(10,10,'Mg',size=10,color=0)))
        large=self.bbox(self.render(lambda c:c.drawText(10,10,'Mg',size=30.5,color=0)))
        multi=self.bbox(self.render(lambda c:c.drawText(10,10,'Mg\n\nMg',size=10,color=0)))
        self.assertGreater(large[2]-large[0],2*(small[2]-small[0]))
        self.assertGreater(multi[3]-multi[1],2*(small[3]-small[1]))
        for options in ({'w':0},{'h':0},{'size':0}):
            self.assertIsNone(self.bbox(self.render(lambda c:c.drawText(10,10,'text',color=0,**options))))

    def test_clipping_and_color_do_not_leak(self):
        def draw(c):
            c.push();c.clipRect(50,50,30,30)
            c.drawText(30,30,'MMMMMMMM\nMMMMMMMM',size=35,color=Color(0xFF0000,.5))
            c.pop()
            c.drawRect(200,180,220,200,fill=0x0000FF)
        im=self.render(draw)
        self.assertEqual(im.getpixel((210,190)),(0,0,255))
        self.assertEqual(im.getpixel((40,40)),(255,255,255))
        reds=[im.getpixel((x,y)) for y in range(50,80) for x in range(50,80)
              if im.getpixel((x,y))[0]>im.getpixel((x,y))[1]+10]
        self.assertTrue(reds)
        self.assertTrue(all(p[1]>=120 for p in reds))
