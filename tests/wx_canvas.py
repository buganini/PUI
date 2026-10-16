"""Native wx Canvas rendering and per-paint style lifetime (GUI required)."""
import importlib.util
import unittest
from unittest.mock import patch

import wx
from PUI.wx.canvas import Canvas
from PUI.common import Anchor


class CanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.GetApp() or wx.App()

    def setUp(self):
        self.window = wx.Frame(None)
        self.canvas = Canvas(lambda c: None)
        self.canvas.ui = wx.Panel(self.window, size=(320, 240))

    def tearDown(self):
        self.window.Destroy()
        self.app.Yield()

    def render(self, operations, isolate=False):
        bitmap = wx.Bitmap(320, 240)
        dc = self.canvas.dc = wx.MemoryDC(bitmap)
        dc.SetBackground(wx.Brush('white'))
        dc.Clear()
        pen, brush = dc.GetPen(), dc.GetBrush()
        try:
            for op in operations:
                if isolate:
                    dc.SetPen(pen)
                    dc.SetBrush(brush)
                op(self.canvas)
        finally:
            dc.SelectObject(wx.NullBitmap)
            self.canvas.dc = None
            self.canvas._clear_paint_styles()
        return bytes(bitmap.ConvertToImage().GetData())

    def test_mixed_styles_text_and_curves_match_isolated_draws(self):
        operations = [
            lambda c: c.drawRect(5, 5, 45, 40, fill=0xCC2233, stroke=0x112244, width=4),
            lambda c: c.drawPolyline([(50, 10), (80, 30), (100, 10)], color=0x22AA33, width=3),
            lambda c: c.drawEllipse(140, 25, 25, 20, stroke=0x3344CC),
            lambda c: c.drawPolygon([(175, 5), (210, 40), (240, 5)], fill=0xCC8844),
            lambda c: c.drawCubicBezier((10, 100), (30, 40), (100, 160), (140, 100), color=0x8833CC, width=2),
            lambda c: c.drawRect(170, 70, 210, 100),
            lambda c: c.drawLine(210, 70, 250, 100),
            lambda c: c.drawText(150, 110, 'Default text'),
            lambda c: c.drawText(20, 165, 'Rotated', color=0xCC3300, rotate=15, anchor=Anchor.CENTER),
            lambda c: c.drawLine(5, 220, 300, 220, color=0x223344, width=2),
        ]
        self.assertEqual(self.render(operations), self.render(operations, isolate=True))

    @unittest.skipUnless(importlib.util.find_spec('shapely'), 'Shapely is not installed')
    def test_nested_geometry_and_holes_do_not_leak_fill(self):
        from shapely.geometry import GeometryCollection, Point, LineString, Polygon
        polygon = Polygon([(20, 20), (100, 20), (100, 100), (20, 100)],
                          holes=[[(40, 40), (80, 40), (80, 80), (40, 80)]])
        shape = GeometryCollection([Point(140, 50), LineString([(120, 20), (170, 100)]),
                                    GeometryCollection([polygon])])
        def draw(c):
            c.drawShapely(shape, fill=0xDD8844, stroke=0x2244CC, width=4)
            c.drawText(10, 140, 'Default after geometry')
        expected = [lambda c: c.drawEllipse(140, 50, 2, 2, fill=0x2244CC),
                    lambda c: c.drawPolyline([(120, 20), (170, 100)], color=0x2244CC, width=4),
                    lambda c: c.drawShapely(polygon, fill=0xDD8844, stroke=0x2244CC, width=4),
                    lambda c: c.drawText(10, 140, 'Default after geometry')]
        self.assertEqual(self.render([draw]), self.render(expected, isolate=True))

    def test_cached_styles_are_reused_and_cleared_after_callback_failure(self):
        self.assertIs(self.canvas._pen(0x112233, 2), self.canvas._pen(0x112233, 2))
        self.assertIs(self.canvas._brush(0x112233), self.canvas._brush(0x112233))
        self.assertIs(self.canvas._font(12), self.canvas._font(12))
        def fail(c):
            c.drawRect(0, 0, 10, 10, fill=0xFF0000, stroke=0)
            raise ValueError('paint failed')
        self.canvas.painter = fail
        bitmap = wx.Bitmap(320, 240)
        dc = wx.MemoryDC(bitmap)
        try:
            with patch('PUI.wx.canvas.wx.PaintDC', return_value=dc):
                with self.assertRaisesRegex(ValueError, 'paint failed'):
                    self.canvas._paint(None)
            self.assertIsNone(self.canvas.dc)
            self.assertEqual((self.canvas._pens, self.canvas._brushes, self.canvas._fonts), ({}, {}, {}))
        finally:
            dc.SelectObject(wx.NullBitmap)


if __name__ == '__main__':
    unittest.main()
