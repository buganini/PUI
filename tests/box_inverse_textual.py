"""Native Textual moves preserve focus, drafts and custom container bookkeeping."""
import unittest
import PUI.textual as UI


class TextualInverse(unittest.IsolatedAsyncioTestCase):
    async def test_box_directions_keep_the_focused_editor(self):
        for kind in ('HBox', 'VBox', 'HVBox', 'VHBox'):
            with self.subTest(kind=kind):
                class Demo(UI.Application):
                    primary = True
                    inverse_h = inverse_v = False
                    def setup(self):
                        self.form = UI.State()
                        self.form.text = 'draft'
                    def content(self):
                        with UI.Window():
                            with UI.VBox().tLayout(weight=1):
                                cls = getattr(UI, kind)
                                if kind in ('HBox', 'VBox'):
                                    box = cls(inverse=self.inverse_h)
                                else:
                                    threshold = {'tMinWidth' if kind == 'HVBox' else 'tMinHeight':
                                                 1 if self.primary else 10000}
                                    box = cls(600, inverseH=self.inverse_h,
                                              inverseV=self.inverse_v, **threshold)
                                with box.tLayout(weight=1) as self.box:
                                    UI.Label('A').id('a').tLayout(width=10, height=3)
                                    UI.TextField(self.form('text')).id('b').tLayout(width=10, height=3)
                                    UI.Label('C').id('c').tLayout(width=10, height=3)
                root = Demo()
                async with root.ui.run_test(size=(80, 30)) as pilot:
                    await pilot.pause()
                    original = {child._id: child.outer for child in root.box.children}
                    editor = original['b']
                    editor.focus()
                    await pilot.press('x')
                    draft = editor.value
                    for primary in (True, False, True):
                        for inverse_h, inverse_v in ((False, False), (True, False),
                                                     (False, True), (True, True)):
                            root.primary = primary
                            root.inverse_h, root.inverse_v = inverse_h, inverse_v
                            root.redraw()
                            await pilot.pause()
                            box = root.box
                            horizontal = kind == 'HBox' if kind in ('HBox', 'VBox') else box.container_x
                            inverse = inverse_h if kind in ('HBox', 'VBox') or horizontal else inverse_v
                            actual = {child._id: child.outer for child in box.children}
                            self.assertEqual(actual, original)
                            positions = [getattr(actual[name].region, 'x' if horizontal else 'y')
                                         for name in ('a', 'b', 'c')]
                            self.assertEqual(positions[0] > positions[2], inverse, positions)
                            self.assertIs(root.ui.focused, editor)
                            self.assertEqual(editor.value, draft)

    async def test_stack_and_grid_keyed_moves_keep_their_native_order(self):
        for cls in (UI.Stack, UI.Grid):
            class Demo(UI.Application):
                names = ('a', 'b', 'c')
                def content(self):
                    with UI.Window():
                        with cls() as self.box:
                            if cls is UI.Grid:
                                self.box.columns(3)
                            for name in self.names:
                                UI.Label(name).id(name)
            root = Demo()
            async with root.ui.run_test(size=(80, 30)) as pilot:
                await pilot.pause()
                for names in (('c', 'b', 'a'), ('b', 'a', 'c'), ('a', 'c'), ('c', 'd', 'a')):
                    root.names = names
                    root.redraw()
                    await pilot.pause()
                    ordered = [child.outer for child in root.box.children]
                    self.assertEqual(list(root.box.ui.children), ordered[::-1] if cls is UI.Stack else ordered)
                    if cls is UI.Grid:
                        self.assertEqual([child.get_node()._id for child in root.box.mounted], list(names))
                        self.assertEqual([widget for widget, cell in root.box.grid_layout.cells], ordered)
