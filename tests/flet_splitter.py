import unittest
import msgpack
from types import SimpleNamespace
import PUI.flet as UI
import flet_regression


class FletSplitter(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = flet_regression.FletRegression.asyncSetUp
    asyncTearDown = flet_regression.FletRegression.asyncTearDown
    mount = flet_regression.FletRegression.mount
    sync = flet_regression.FletRegression.sync

    async def test_drag_retains_controls_and_reconciles_orientation_and_panes(self):
        class Demo(UI.Application):
            vertical = False
            order = ['a', 'b', 'c']
            hidden = False
            def content(self):
                with UI.Window():
                    with UI.Splitter(vertical=self.vertical).layout(weight=1) as self.split:
                        for key in self.order:
                            with UI.VBox().id(key).visible(not(self.hidden and key == 'b')):
                                UI.TextField(UI.DummyBinding(key))
        await self.mount(Demo())
        # Registration both mounts the tree and serializes Flet's first snapshot.
        msgpack.packb(self.session.get_page_patch(), default=self.connection.encoder)
        split = self.root.split
        editor = split.children[0].children[0].ui
        panes = split.panes
        for frame in panes.frames.values():
            await frame.on_size_change(SimpleNamespace(width=300, height=400))
        handle = panes.handles[0]
        await handle.on_horizontal_drag_start(SimpleNamespace(global_position=UI.ft.Offset(300, 30)))
        await handle.on_horizontal_drag_update(SimpleNamespace(global_position=UI.ft.Offset(380, 30)))
        frames = list(panes.frames.values())
        self.assertGreater(frames[0].expand, frames[1].expand)
        self.assertEqual(frames[2].expand, 10000)
        weights = [frame.expand for frame in frames]
        self.sync()
        self.assertIs(self.root.split.panes, panes)
        self.assertIs(self.root.split.children[0].children[0].ui, editor)
        self.assertEqual([frame.expand for frame in frames], weights)
        self.root.vertical = True
        self.sync()
        self.assertIsInstance(self.root.split.ui, UI.ft.Column)
        self.assertIs(self.root.split.children[0].children[0].ui, editor)
        for frame in panes.frames.values():
            await frame.on_size_change(SimpleNamespace(width=300, height=200))
        handle = panes.handles[0]
        await handle.on_vertical_drag_start(SimpleNamespace(global_position=UI.ft.Offset(30, 200)))
        await handle.on_vertical_drag_update(SimpleNamespace(global_position=UI.ft.Offset(30, 250)))
        self.assertGreater(frames[0].expand, frames[1].expand)
        self.root.order = ['c', 'a']
        self.sync()
        self.assertIs(self.root.split.children[1].children[0].ui, editor)
        self.assertEqual(len(panes.handles), 1)
        for order in ([], ['a'], ['a', 'b']):
            self.root.order = order
            self.sync()
            self.assertEqual(len(panes.handles), max(0, len(order) - 1))
        self.root.hidden = True
        self.sync()
        self.assertEqual(len(panes.handles), 0)

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
        await self.mount(Demo())
        view = self.root.split.children[0]
        for order in (['c', 'a', 'b'], [], ['a']):
            view.order = order
            view.sync()
            self.assertEqual(len(self.root.split.panes.widgets), len(order))
            self.assertEqual(len(self.root.split.panes.handles), max(0, len(order) - 1))
