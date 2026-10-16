"""Precise Tk touchpad event integration; requires Tk 8.7+ or 9 and a display."""
import unittest
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk
from PUI.tkinter.scroll import ScrollableFrame


class TouchpadTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        if not self.root.tk.call('info', 'commands', 'tk::ScrollByPixels'):
            self.skipTest('Tk does not support precise touchpad scrolling')
        self.root.geometry('300x200')
        self.scroll = ScrollableFrame(self.root)
        self.scroll.puinode = SimpleNamespace(align_x=0, align_y=0)
        self.scroll.container.pack(fill='both', expand=True)
        self.label = ttk.Label(self.scroll, text='long content', width=150)
        self.label.grid()
        ttk.Frame(self.scroll, height=1500).grid(row=1)
        self.scroll.set_scroll(True, True)
        self.root.update()
        self.scroll.canvas.xview_moveto(.3)
        self.scroll.canvas.yview_moveto(.3)
        self.root.update()

    def gesture(self, dx, dy, state=0):
        packed = (dx << 16) | (dy & 0xffff)
        self.label.event_generate('<TouchpadScroll>', delta=packed, state=state)
        self.root.update()

    def test_precise_gestures_move_both_axes_and_reverse(self):
        canvas = self.scroll.canvas
        x, y = canvas.xview()[0], canvas.yview()[0]
        self.gesture(-12, -20)
        self.assertGreater(canvas.xview()[0], x)
        self.assertGreater(canvas.yview()[0], y)
        after = canvas.yview()[0]
        self.gesture(0, 10)
        self.assertLess(canvas.yview()[0], after)

    def test_disabled_axis_is_ignored(self):
        self.scroll.should_scroll_x = False
        x = self.scroll.canvas.xview()
        self.gesture(-20, -10)
        self.assertEqual(self.scroll.canvas.xview(), x)

    def test_unrelated_widget_does_not_scroll_and_bindings_are_removed(self):
        other = ttk.Label(self.root, text='outside')
        before = self.scroll.canvas.yview()
        other.event_generate('<TouchpadScroll>', delta=65516)
        self.root.update()
        self.assertEqual(self.scroll.canvas.yview(), before)
        token = self.scroll.wheel_bindings['<TouchpadScroll>']
        self.scroll.container.destroy()
        self.assertNotIn(token, self.root.bind('<TouchpadScroll>'))
