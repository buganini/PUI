import unittest
import PUI.textual as UI


class TextualSplitter(unittest.IsolatedAsyncioTestCase):
    async def test_pointer_keyboard_orientation_and_retained_editor(self):
        class Demo(UI.Application):
            vertical = False
            order = ['a', 'b', 'c']
            hidden = False
            def setup(self):
                self.form = UI.State()
                self.form.text = ''
            def content(self):
                with UI.Window():
                    with UI.Splitter(vertical=self.vertical).layout(weight=1) as self.split:
                        for key in self.order:
                            with UI.VBox().id(key).visible(not(self.hidden and key == 'b')):
                                UI.TextField(self.form('text'))
        root = Demo()
        async with root.ui.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            host = root.split.ui
            editor = root.split.children[0].children[0].ui
            editor.focus()
            await pilot.press(*'draft')
            await pilot.pause()
            handle = host.handles[0]
            before = host.panes[0].region.width
            destination = (handle.region.x + 9, handle.region.y)
            await pilot.mouse_down(handle)
            await pilot.hover(offset=destination)
            await pilot.mouse_up(offset=destination)
            await pilot.pause()
            self.assertGreater(host.panes[0].region.width, before + 5)
            ratio = list(host.weights)
            root.sync()
            await pilot.pause()
            self.assertEqual(host.weights, ratio)
            self.assertIs(root.split.children[0].children[0].ui, editor)
            self.assertEqual(editor.value, 'draft')
            handle.focus()
            before = host.panes[0].region.width
            await pilot.press('left')
            await pilot.pause()
            self.assertLess(host.panes[0].region.width, before)
            root.vertical = True
            root.sync()
            await pilot.pause()
            self.assertIs(root.split.children[0].children[0].ui, editor)
            self.assertLess(host.panes[0].region.y, host.panes[1].region.y)
            root.order = ['c', 'a']
            root.sync()
            await pilot.pause()
            self.assertIs(root.split.children[1].children[0].ui, editor)
            self.assertEqual(len(host.handles), 1)
            for order in ([], ['b'], ['a', 'b']):
                root.order = order
                root.sync()
                await pilot.pause()
                self.assertEqual(len(host.handles), max(0, len(order) - 1))
            root.hidden = True
            root.sync()
            await pilot.pause()
            self.assertEqual(len(host.handles), 0)

    async def test_independent_view_updates_panes(self):
        class Panes(UI.PUIView):
            order = ['a', 'b']
            def content(self):
                for key in self.order:
                    UI.Label(key).id(key)
        class Demo(UI.Application):
            def content(self):
                with UI.Window():
                    with UI.Splitter() as self.split:
                        Panes()
        root = Demo()
        async with root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            view = root.split.children[0]
            for order in (['c', 'a', 'b'], [], ['a']):
                view.order = order
                view.sync()
                await pilot.pause()
                self.assertEqual(len(root.split.ui.panes), len(order))
                self.assertEqual(len(root.split.ui.handles), max(0, len(order) - 1))
