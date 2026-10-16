"""Native Tk Canvas paint defaults and cache lifetime; requires a display."""
import tkinter as tk
from tkinter import font as tkfont, ttk
import unittest
from unittest.mock import patch

from PUI.tkinter.canvas import Canvas


class CanvasTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.canvas = Canvas(lambda c: None)
        self.canvas.ui = tk.Canvas(self.root, width=320, height=240)

    def test_defaults_are_read_once_per_paint_and_refresh_next_frame(self):
        canvas = self.canvas
        def paint(c):
            c.drawText(0, 0, 'default', size=None)
            c.drawText(0, 20, 'default again', size=None)
            c.drawText(0, 40, 'explicit', size=10, color=0x123456)
        canvas.painter = paint
        font = tkfont.nametofont('TkDefaultFont', root=self.root)
        style = ttk.Style(self.root)
        for size, color in ((14, '#123456'), (18, '#abcdef')):
            font.configure(size=size)
            style.configure('TLabel', foreground=color)
            with patch('PUI.tkinter.canvas.tkFont.nametofont', wraps=tkfont.nametofont) as lookup:
                with patch.object(canvas, '_text_color', wraps=canvas._text_color) as text_color:
                    canvas.paint()
                    self.assertEqual(lookup.call_count, 1)
                    self.assertEqual(text_color.call_count, 1)
            items = canvas.ui.find_all()
            for item in items[:2]:
                self.assertEqual(canvas.ui.itemcget(item, 'fill'), color)
                self.assertEqual(tkfont.Font(self.root, font=canvas.ui.itemcget(item, 'font')).actual('size'), size)
                self.assertIn('pui_theme_text', canvas.ui.gettags(item))
            self.assertEqual(canvas.ui.itemcget(items[2], 'fill'), '#123456')
            self.assertEqual(tkfont.Font(self.root, font=canvas.ui.itemcget(items[2], 'font')).actual('size'), 10)
            self.assertNotIn('pui_theme_text', canvas.ui.gettags(items[2]))
            self.assertEqual(canvas._paint_colors, {})
            self.assertIsNone(canvas._paint_font)
            self.assertIsNone(canvas._paint_text_color)

    def test_mixed_geometry_matches_native_options_and_clears_all_items(self):
        canvas = self.canvas
        def paint(c):
            c.drawLine(0, 0, 10, 20, color=0x123456, width=None)
            c.ui.create_line(1, 2, 3, 4, fill='red')  # Native drawings still work.
            c.drawPolyline([(1, 2), (3, 4), (5, 6)], color=0x123456, width=2)
            c.drawRect(40, 30, 10, 20, fill=0x123456)
            c.drawPolygon([(0, 0), (5, 0), (5, 5)], stroke=0x123456, width=3)
            c.drawEllipse(50, 50, 5, 10, fill=0x123456, stroke=0)
            c.drawLine(1, 2, 3, 4)  # None still omits the line.
        canvas.painter = paint
        expected = tk.Canvas(self.root)
        expected.create_line(0, 0, 10, 20, fill='#123456')
        expected.create_line(1, 2, 3, 4, fill='red')
        expected.create_line(1, 2, 3, 4, 5, 6, fill='#123456', width=2)
        expected.create_rectangle(10, 20, 40, 30, fill='#123456', outline='', width=1)
        expected.create_polygon(0, 0, 5, 0, 5, 5, fill='', outline='#123456', width=3)
        expected.create_oval(45, 40, 55, 60, fill='#123456', outline='#000000', width=1)
        def snapshot(widget):
            return [(widget.type(item), widget.coords(item), widget.itemconfigure(item))
                    for item in widget.find_all()]
        previous = set()
        for _ in range(2):
            canvas.paint()
            self.assertEqual(snapshot(canvas.ui), snapshot(expected))
            current = set(canvas.ui.find_all())
            self.assertFalse(current & previous)
            previous = current
        canvas.painter = lambda c: None
        canvas.paint()
        self.assertEqual(canvas.ui.find_all(), ())

    def test_failed_callback_drops_styles_and_next_frame_rebuilds(self):
        canvas = self.canvas
        def fail(c):
            c.drawText(0, 0, 'before error')
            c.drawRect(1, 2, 3, 4, fill=0x123456)
            raise ValueError('paint failed')
        canvas.painter = fail
        with self.assertRaisesRegex(ValueError, 'paint failed'):
            canvas.paint()
        self.assertEqual(canvas._paint_colors, {})
        self.assertIsNone(canvas._paint_font)
        self.assertIsNone(canvas._paint_text_color)
        previous = set(canvas.ui.find_all())
        canvas.painter = lambda c: c.drawRect(1, 2, 3, 4, fill=0xABCDEF)
        canvas.paint()
        self.assertFalse(previous & set(canvas.ui.find_all()))
        self.assertEqual(canvas.ui.itemcget(canvas.ui.find_all()[0], 'fill'), '#ABCDEF')
