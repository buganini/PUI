"""QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p pyside6_layout.py"""
import contextlib
import io
import unittest

import PUI.PySide6 as UI
from PUI.dom import recur_delete
from PySide6 import QtWidgets


class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.root = None

    def tearDown(self):
        if self.root is not None:
            self.root.ui = None  # The test suite owns the shared QApplication.
            recur_delete(self.root, self.root, True)
            self.app.processEvents()

    def mount(self, content):
        class Demo(UI.Application):
            def content(self):
                with UI.Window(size=(800, 600)):
                    content(self)
        self.root = Demo()
        self.root.ui = self.app
        self.sync()

    def sync(self, node=None):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            (node or self.root).sync()
            for _ in range(8):
                self.app.processEvents()
        self.assertNotIn('<ERROR', output.getvalue())
        self.assertNotIn('Traceback', output.getvalue())

    def test_static_children_keep_size_and_pack_at_start(self):
        horizontal = inverse = False
        def content(root):
            box = UI.HBox if horizontal else UI.VBox
            with box(inverse=inverse).layout(padding=0) as root.box:
                root.first = UI.Label('First')
                UI.Divider()
                root.last = UI.Label('Last')
        self.mount(content)
        for horizontal in (False, True):
            for inverse in (False, True):
                self.sync()
                for node in (self.root.first, self.root.last):
                    self.assertEqual(node.ui.size(), node.ui.sizeHint())
                    if horizontal:
                        self.assertLessEqual(abs(node.ui.geometry().center().y() - 299), 1)
                    else:
                        self.assertEqual(node.ui.x(), 0)
                nodes = [self.root.first, self.root.last]
                positions = [n.ui.x() if horizontal else n.ui.y() for n in nodes]
                self.assertEqual(positions[0] > positions[1], inverse)
                self.assertEqual(min(positions), 0)

    def test_priorities_resize_visibility_and_weight_restore(self):
        horizontal, canvas_visible, spacer_visible, canvas_weight = False, True, False, None
        def content(root):
            box = UI.HBox if horizontal else UI.VBox
            other = UI.VBox if horizontal else UI.HBox
            with box().layout(padding=0) as root.box:
                with box().layout(padding=0) as root.along:
                    UI.Label('Along')
                with other().layout(padding=0) as root.across:
                    UI.Label('Across')
                root.canvas = UI.Canvas(lambda c: None).layout(width=40, height=40, weight=canvas_weight).visible(canvas_visible)
                root.spacer = UI.Spacer().visible(spacer_visible)
        self.mount(content)
        for horizontal in (False, True):
            for canvas_visible, spacer_visible, canvas_weight, winner in (
                (True, False, None, 'canvas'), (False, False, None, 'along'),
                (True, True, None, 'spacer'), (True, False, 0, 'along'),
                (True, False, None, 'canvas'),
            ):
                self.sync()
                retained = self.root.canvas.ui
                for size in ((800, 600), (650, 450)):
                    self.root.children[0].ui.resize(*size)
                    for _ in range(5): self.app.processEvents()
                    for name in ('along', 'across', 'canvas', 'spacer'):
                        node = getattr(self.root, name)
                        if not node._visible:
                            continue
                        rect = node.ui.geometry()
                        extent = rect.width() if horizontal else rect.height()
                        if name == winner:
                            self.assertGreater(extent, 300, (horizontal, winner, name, rect))
                        else:
                            self.assertLess(extent, 150, (horizontal, winner, name, rect))
                    self.assertIs(self.root.canvas.ui, retained)

    def test_weighted_static_controls_expand_and_reset(self):
        weight = 1
        def content(root):
            with UI.VBox().layout(padding=0):
                root.label = UI.Label('Weighted').layout(weight=weight)
                root.spacer = UI.Spacer()
        self.mount(content)
        original = self.root.label.ui
        for weight in (1, 2, 0, None, 1):
            self.sync()
            self.assertIs(self.root.label.ui, original)
            if weight:
                self.assertAlmostEqual(original.height(), self.root.spacer.ui.geometry().height() * weight, delta=2)
            else:
                self.assertEqual(original.height(), original.sizeHint().height())

    def test_independent_nested_view_recalculates_sibling_competition(self):
        class Fragment(UI.PUIView):
            show_canvas = False
            def content(view):
                if view.show_canvas:
                    UI.Canvas(lambda c: None).layout(width=40, height=40)
                else:
                    UI.Label('Static')
        def content(root):
            with UI.VBox().layout(padding=0) as root.box:
                with UI.VBox().layout(padding=0) as root.sibling:
                    UI.Label('Sibling')
                root.fragment = Fragment()
        self.mount(content)
        for shown in (True, False, True):
            self.root.fragment.show_canvas = shown
            self.sync(self.root.fragment)
            if shown:
                self.assertLess(self.root.sibling.ui.height(), 50)
                self.assertGreater(self.root.fragment.children[0].ui.geometry().height(), 500)
            else:
                self.assertGreater(self.root.sibling.ui.height(), 500)

    def test_scroll_content_keeps_natural_height(self):
        def content(root):
            with UI.VBox().layout(padding=0):
                UI.Label('Heading')
                with UI.Scroll().layout(weight=1) as root.scroll:
                    with UI.VBox().layout(padding=0) as root.rows:
                        for i in range(80):
                            UI.Label(str(i))
        self.mount(content)
        self.assertGreater(self.root.scroll.ui.verticalScrollBar().maximum(), 500)
        for row in self.root.rows.children:
            self.assertEqual(row.ui.height(), row.ui.sizeHint().height())

    def test_native_policy_override_can_be_removed(self):
        override = True
        def content(root):
            with UI.HBox().layout(padding=0):
                root.label = UI.Label('Native override')
                if override:
                    root.label.qt(HorizontalPolicy=QtWidgets.QSizePolicy.Expanding)
        self.mount(content)
        for override in (True, False, True):
            self.sync()
            if override:
                self.assertEqual(self.root.label.ui.width(), 800)
            else:
                self.assertEqual(self.root.label.ui.width(), self.root.label.ui.sizeHint().width())

    def test_wrapped_native_editor_keeps_expansion_and_contents(self):
        editor = QtWidgets.QTextEdit()
        editor.setPlainText('Native draft')
        def content(root):
            with UI.VBox().layout(padding=0):
                UI.Label('Heading')
                UI.QtInPui(editor)
        self.mount(content)
        for _ in range(3):
            self.sync()
            self.assertGreater(editor.height(), 500)
            self.assertEqual(editor.toPlainText(), 'Native draft')
