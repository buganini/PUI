"""Native linear layout checks for doc/Layout.html."""
import unittest
from PUI.tkinter import Application, Window, VBox, HBox, Label, Scroll, Spacer
from PUI.dom import recur_delete


class SizingTests(unittest.TestCase):
    def mount(self, content):
        class Example(Application):
            def content(self):
                with Window(size=(600, 500)):
                    content()
        self.app = Example()
        self.addCleanup(lambda: recur_delete(self.app, self.app, True))
        self.app.sync()
        self.app.ui.update()
        return self.app.children[0].children[0]

    def test_nested_growable_container_expands_without_descendant_promotion(self):
        def content():
            with VBox():
                Label('header')
                with VBox():
                    with Scroll():
                        Label('content')
        box = self.mount(content)
        inner = box.children[1]
        self.assertEqual(box.ui.grid_rowconfigure(1)['weight'], 1)
        self.assertGreater(inner.ui.winfo_height(), 400)
        self.assertEqual(inner.children[0].outer.winfo_height(), inner.ui.winfo_height())

    def test_weighted_sibling_suppresses_scroll_and_nested_weight(self):
        def content():
            with VBox():
                with Scroll():
                    Label('scroll')
                with VBox():
                    Spacer()
                Spacer()
        box = self.mount(content)
        self.assertEqual([box.ui.grid_rowconfigure(i)['weight'] for i in range(3)], [0, 0, 1])

    def test_scroll_beats_growable_and_static_siblings(self):
        def content():
            with VBox():
                Label('header')
                with VBox():
                    Label('compact box')
                with Scroll():
                    Label('scroll')
        box = self.mount(content)
        self.assertEqual([box.ui.grid_rowconfigure(i)['weight'] for i in range(3)], [0, 0, 1])
        self.assertEqual(box.children[0].ui.winfo_width(), box.children[0].ui.winfo_reqwidth())
        self.assertEqual(box.children[0].ui.winfo_x(), 0)

    def test_explicit_weights_split_space_and_reset_after_redraw(self):
        def content():
            with HBox():
                VBox().layout(weight=1)
                VBox().layout(weight=2)
        box = self.mount(content)
        a, b = box.children
        self.assertAlmostEqual(b.ui.winfo_width() / a.ui.winfo_width(), 2, delta=.05)
        b.layout_weight = 0
        box.postSync()
        self.app.ui.update()
        self.assertEqual(box.ui.grid_columnconfigure(1)['weight'], 0)

    def test_canvas_in_scroll_tracks_viewport_width_and_repaints(self):
        from PUI.tkinter import Canvas
        painted = []
        def content():
            with VBox():
                with Scroll():
                    Canvas(lambda c: painted.append((c.width, c.height))).layout(height=720, weight=1)
        box = self.mount(content)
        scroll = box.children[0]
        canvas = scroll.children[0]
        for size in ('600x500', '800x500', '450x500'):
            self.app.children[0].ui.geometry(size)
            self.app.ui.update()
            self.assertEqual(canvas.ui.winfo_width(), scroll.ui.canvas.winfo_width())
            self.assertEqual(canvas.ui.winfo_height(), 720)
            self.assertEqual(painted[-1], (canvas.ui.winfo_width(), 720))

    def test_text_dimensions_use_pixels_and_follow_font_changes(self):
        from tkinter import font
        def content():
            with VBox():
                Label('tile').layout(width=160, height=60)
        label = self.mount(content).children[0]
        for size in (10, 20):
            label.style_fontsize = size
            label.update(label)
            self.app.ui.update()
            metrics = font.Font(root=label.ui, font=label.ui.cget('font'))
            self.assertGreaterEqual(label.ui.winfo_reqheight(), 60)
            self.assertLess(label.ui.winfo_reqheight(), 60 + metrics.metrics('linespace'))
            self.assertGreaterEqual(label.ui.winfo_reqwidth(), 160)
            self.assertLess(label.ui.winfo_reqwidth(), 160 + metrics.measure('0'))
        label.layout_width = label.layout_height = None
        label.update(label)
        self.assertEqual(int(label.ui.cget('height')), 0)
        self.assertEqual(int(label.ui.cget('width')), 0)

    def test_grid_label_rowspans_do_not_request_hundreds_of_text_lines(self):
        from PUI.tkinter import Grid
        def content():
            with Scroll():
                with Grid().columns(3):
                    for rows in (1, 2, 3):
                        Label('tile').grid(rowspan=rows).layout(height=rows * 60)
        grid = self.mount(content).children[0]
        for label in grid.children:
            self.assertGreaterEqual(label.ui.winfo_reqheight(), label.layout_height)
            self.assertLess(label.ui.winfo_reqheight(), label.layout_height + 30)
        self.assertLess(grid.ui.winfo_reqheight(), 300)
