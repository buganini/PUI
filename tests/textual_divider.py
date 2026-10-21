"""Native Rule rendering, compact sizing and retained adaptive orientation."""
import unittest

from textual.widgets import Rule
import PUI.textual as UI


class TextualDividerTests(unittest.IsolatedAsyncioTestCase):
    def check_line(self, box, line):
        vertical = box.container_x
        self.assertIsInstance(line.ui, Rule)
        self.assertEqual(line.ui.orientation, 'vertical' if vertical else 'horizontal')
        region, content = line.ui.region, box.ui.content_region
        self.assertEqual(region.width if vertical else region.height, 1)
        self.assertEqual(region.height if vertical else region.width,
                         content.height if vertical else content.width)
        self.assertGreater(region.height if vertical else region.width, 0)
        glyph = '│' if vertical else '─'
        for y in range(region.height):
            self.assertEqual(line.ui.render_line(y).text, glyph * region.width)

    async def test_compact_and_expanding_boxes_through_virtual_view(self):
        class Line(UI.PUIView):
            def content(self):
                UI.Divider()

        class Demo(UI.Application):
            def content(self):
                with UI.Window():
                    with UI.VBox().layout(weight=1):
                        with UI.HBox() as self.compact:
                            UI.Label('Before')
                            Line()
                            UI.Button('After')
                        with UI.VBox() as self.column:
                            UI.Label('Above')
                            Line()
                            UI.Label('Below')
                        with UI.HBox().layout(weight=1) as self.expanding:
                            UI.Label('Before')
                            Line()
                            UI.Label('After')

        root = Demo()
        async with root.ui.run_test(size=(80, 30)) as pilot:
            for width, height in ((80, 30), (100, 40), (60, 24)):
                await pilot.resize_terminal(width, height)
                await pilot.pause()
                for box in (root.compact, root.column, root.expanding):
                    self.check_line(box, box.children[1].children[0])
                    self.assertLessEqual(box.ui.region.bottom, height)
                self.assertEqual(root.compact.ui.region.height,
                                 root.compact.children[2].ui.region.height)
                self.assertEqual(root.column.ui.region.height, 5)  # Rule's native margins.

    async def test_adaptive_resize_retains_native_rule(self):
        class Line(UI.PUIView):
            def content(self):
                UI.Divider()

        for kind in ('HVBox', 'VHBox'):
            with self.subTest(kind=kind):
                class Demo(UI.Application):
                    def content(self):
                        with UI.Window():
                            with UI.VBox().layout(weight=1):
                                kwargs = {'tMinWidth': 60} if kind == 'HVBox' else {'tMinHeight': 30}
                                with getattr(UI, kind)(600, **kwargs).layout(weight=1) as self.box:
                                    UI.Label('Before')
                                    UI.Divider()
                                    Line()
                                    UI.Label('After')

                root = Demo()
                async with root.ui.run_test(size=(80, 40)) as pilot:
                    await pilot.pause()
                    native = root.box.children[1].ui
                    nested = root.box.children[2].children[0].ui
                    for width, height in ((50, 20), (80, 40), (50, 40), (80, 20)):
                        await pilot.resize_terminal(width, height)
                        await pilot.pause()
                        vertical = width >= 60 if kind == 'HVBox' else height < 30
                        self.assertEqual(root.box.container_x, vertical)
                        line = root.box.children[1]
                        self.assertIs(line.ui, native)
                        self.check_line(root.box, line)
                        line = root.box.children[2].children[0]
                        self.assertIs(line.ui, nested)
                        self.check_line(root.box, line)

    async def test_theme_style_reset_and_visibility(self):
        class Demo(UI.Application):
            styled = False
            shown = True

            def content(self):
                with UI.Window():
                    with UI.VBox() as self.box:
                        UI.Label('Above')
                        self.line = UI.Divider().tVisible(self.shown)
                        if self.styled:
                            self.line.tStyle(color=0xFF0000).tLayout(margin=0)
                        UI.Label('Below')

        root = Demo()
        async with root.ui.run_test(size=(80, 30)) as pilot:
            await pilot.pause()
            native = root.line.ui
            for theme in ('textual-dark', 'textual-light'):
                root.ui.theme = theme
                await pilot.pause()
                theme_color = native.styles.color
                for styled, shown in ((True, True), (False, False), (False, True)):
                    root.styled, root.shown = styled, shown
                    root.redraw()
                    await pilot.pause()
                    self.assertIs(root.line.ui, native)
                    self.assertEqual(native.display, shown)
                    if shown:
                        self.check_line(root.box, root.line)
                        color = next(s.style.color for s in native.render_line(0) if s.text.strip())
                        self.assertEqual(color.get_truecolor(),
                                         (255, 0, 0) if styled else theme_color.rgb)
                        self.assertEqual(tuple(native.styles.margin),
                                         (0, 0, 0, 0) if styled else (1, 0, 1, 0))
                    else:
                        above, _, below = root.box.children
                        self.assertEqual(below.ui.region.y, above.ui.region.bottom)
