"""QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p pyside6_canvas.py"""
import importlib.util
import unittest
from contextlib import contextmanager
from unittest.mock import patch

available = importlib.util.find_spec('PySide6') is not None
if available:
    from PUI.PySide6.canvas import Canvas, ImageResource, PUIQtCanvas
    from PUI.common import Anchor
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QPen, QBrush
    from PySide6.QtWidgets import QApplication, QWidget


@unittest.skipUnless(available, 'PySide6 is not installed')
class CanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.canvas = object.__new__(Canvas)
        self.canvas.ui = QWidget()
        self.canvas.ui.resize(320, 240)

    def tearDown(self):
        self.canvas.ui.close()
        self.canvas.ui.deleteLater()
        self.app.processEvents()

    @contextmanager
    def painting(self, default_color=0x222222):
        image = QImage(320, 240, QImage.Format_ARGB32_Premultiplied)
        image.fill(QColor('white'))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(default_color))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor('cyan')))
        self.canvas._begin_paint(painter)
        try:
            yield image, painter
        finally:
            painter.end()
            self.canvas._end_paint()

    def render(self, operations, isolate=False):
        with self.painting() as (image, painter):
            for op in operations:
                if isolate:
                    painter.save()
                    painter.setPen(self.canvas._default_pen)
                    painter.setBrush(self.canvas._default_brush)
                op(self.canvas)
                if isolate:
                    painter.restore()
        return image

    def test_mixed_primitives_do_not_inherit_previous_styles(self):
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
            lambda c: c.drawText(150, 170, 'Default again', size=None),
            lambda c: c.drawLine(5, 220, 300, 220, color=0x223344, width=2),
        ]
        self.assertEqual(self.render(operations), self.render(operations, isolate=True))

    def test_default_text_after_hidden_or_colored_strokes(self):
        for color in (None, 0xCC0033):
            with self.subTest(color=color):
                text = lambda c: c.drawText(10, 10, 'Visible default', size=None)
                actual = self.render([lambda c: c.drawLine(-20, -20, -10, -10, color=color), text])
                expected = self.render([text])
                self.assertEqual(actual, expected)
                with self.painting() as (blank, _):
                    pass
                self.assertNotEqual(actual, blank)

    def test_styles_are_reused_only_within_the_current_frame(self):
        for default in (0x112233, 0x445566):
            with self.painting(default) as (_, painter):
                pen = self.canvas._pen(0xAABBCC, 3)
                brush = self.canvas._brush(0xAABBCC)
                self.assertIs(self.canvas._pen(0xAABBCC, 3), pen)
                self.assertIs(self.canvas._brush(0xAABBCC), brush)
                self.assertEqual(pen.capStyle(), Qt.RoundCap)
                self.assertEqual(pen.joinStyle(), Qt.RoundJoin)
                self.assertEqual(self.canvas._default_pen.color(), QColor(default))
                # Mutating the active painter's implicitly shared pen does not
                # modify the cached pen used by subsequent helpers.
                painter.setPen(pen)
                changed = painter.pen()
                changed.setColor(QColor('red'))
                painter.setPen(changed)
                self.assertEqual(pen.color(), QColor(0xAABBCC))
            self.assertIsNone(self.canvas.qpainter)
            self.assertEqual(self.canvas._pens, {})
            self.assertEqual(self.canvas._brushes, {})

    def test_mutable_qcolor_inputs_are_not_stale_cache_keys(self):
        color = QColor('red')
        with self.painting():
            self.canvas.drawRect(0, 0, 10, 10, fill=color, stroke=color)
            color.setRgb(0, 0, 255)
            self.canvas.drawRect(20, 0, 30, 10, fill=color, stroke=color)
            self.assertEqual(self.canvas.qpainter.pen().color(), QColor('blue'))
            self.assertEqual(self.canvas.qpainter.brush().color(), QColor('blue'))

    def test_text_and_images_preserve_transform_clip_font_and_opacity(self):
        resource = ImageResource()
        resource.qimage = QImage(10, 10, QImage.Format_ARGB32_Premultiplied)
        resource.qimage.fill(QColor('red'))
        with self.painting() as (_, painter):
            painter.translate(3, 4)
            painter.setClipRect(0, 0, 200, 150)
            painter.setOpacity(0.6)
            before = (painter.transform(), painter.clipRegion(), painter.font(), painter.opacity())
            self.canvas.drawText(20, 30, 'Rotated', rotate=45, size=20, color=0xFF0000)
            self.canvas.drawImage(resource, opacity=0.2)
            after = (painter.transform(), painter.clipRegion(), painter.font(), painter.opacity())
            self.assertEqual(before, after)

    @unittest.skipUnless(importlib.util.find_spec('shapely') is not None, 'Shapely is not installed')
    def test_nested_shapely_geometry_restores_each_requested_style(self):
        from shapely.geometry import GeometryCollection, Point, LineString, Polygon
        polygon = Polygon([(20, 20), (100, 20), (100, 100), (20, 100)],
                          holes=[[(40, 40), (80, 40), (80, 80), (40, 80)]])
        shape = GeometryCollection([Point(140, 50), LineString([(120, 20), (170, 100)]),
                                    GeometryCollection([polygon])])
        def draw(c):
            c.drawShapely(shape, fill=0xDD8844, stroke=0x2244CC, width=3)
            c.drawText(10, 140, 'Default after geometry')
        expected = [lambda c: c.drawEllipse(140, 50, 1.5, 1.5, fill=0x2244CC),
                    lambda c: c.drawPolyline([(120, 20), (170, 100)], color=0x2244CC, width=3),
                    lambda c: c.drawShapely(polygon, fill=0xDD8844, stroke=0x2244CC, width=3),
                    lambda c: c.drawText(10, 140, 'Default after geometry')]
        self.assertEqual(self.render([draw]), self.render(expected, isolate=True))

    def test_failed_callback_ends_painter_and_drops_frame_cache(self):
        def fail(canvas):
            canvas.drawRect(0, 0, 10, 10, fill=0xFF0000, stroke=0x000000)
            raise ValueError('paint failed')
        node = Canvas(fail)
        widget = PUIQtCanvas(node, 320, 240)
        target = QImage(320, 240, QImage.Format_ARGB32_Premultiplied)
        painter = QPainter(target)
        try:
            with patch('PUI.PySide6.canvas.QPainter', return_value=painter) as factory:
                factory.Antialiasing = QPainter.Antialiasing
                with self.assertRaisesRegex(ValueError, 'paint failed'):
                    widget.paintEvent(None)
            self.assertFalse(painter.isActive())
            self.assertIsNone(node.qpainter)
            self.assertEqual(node._pens, {})
            self.assertEqual(node._brushes, {})
        finally:
            widget.close()
            widget.deleteLater()


if __name__ == '__main__':
    unittest.main()
