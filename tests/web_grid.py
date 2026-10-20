import asyncio
import unittest
from PUI.web import Application, Window, Grid, Label, TextField, State
from PUI.web.runtime import Runtime


class WebGrid(unittest.IsolatedAsyncioTestCase):
    async def test_reflow_changes_cells_without_rotating_nodes_or_bindings(self):
        class Demo(Application):
            count = 3
            hide = False
            def setup(self):
                self.form = State()
                self.form.text = 'retained'
            def content(self):
                with Window():
                    with Grid().columns(self.count).dense(True).id('grid'):
                        Label('A').id('a').grid(columnspan=2).visible(not self.hide)
                        Label('B').id('b').grid(columnspan=2)
                        Label('C').id('c')
                        TextField(self.form('text')).id('editor')
        runtime = Runtime(asyncio.get_running_loop())
        runtime.app = root = Demo()
        def sync():
            root.sync()
            runtime.flush()
            snapshot = runtime.snapshot()
            return snapshot, {e.node._id: e for e in runtime.nodes.values()}
        try:
            first, nodes = sync()
            identities = {key: value.id for key, value in nodes.items()}
            attachment = nodes['editor'].attachments['model']['token']
            for count in (1, 3, 2, 3):
                root.count = count
                state, nodes = sync()
                self.assertEqual({key: value.id for key, value in nodes.items()}, identities)
                self.assertEqual(nodes['editor'].attachments['model']['token'], attachment)
                def walk(nodes):
                    for node in nodes:
                        yield node
                        yield from walk(node['children'])
                records = list(walk(state['roots']))
                grid = next(n for n in records if n['props'].get('columns') == count)
                self.assertEqual(grid['props']['columns'], count)
                tile = next(n for n in records if n['id'] == nodes['a'].id)
                self.assertEqual(tile['layout']['columnspan'], min(count, 2))
            root.hide = True
            _, nodes = sync()
            self.assertIsNone(nodes['a'].node._grid_cell)
            self.assertEqual(nodes['b'].node._grid_cell[:2], (0, 0))
        finally:
            runtime.close()

    async def test_virtual_view_updates_reflow_and_auto_to_manual_removes_old_roots(self):
        from PUI.web import PUIView
        class Cards(PUIView):
            count = 2
            def content(self):
                for i in range(self.count):
                    Label(str(i)).id(str(i))
        class Demo(Application):
            automatic = True
            def content(self):
                with Window():
                    with Grid() as self.grid:
                        if self.automatic:
                            self.grid.columns(2)
                            Cards()
                        else:
                            Label('manual').grid(row=0, column=0)
        runtime = Runtime(asyncio.get_running_loop())
        runtime.app = root = Demo()
        try:
            root.sync()
            runtime.flush()
            cards = root.grid.children[0]
            cards.count = 3
            cards.sync()
            self.assertEqual([e.node._grid_cell for e in root.grid.ui.children],
                             [(0, 0, 1, 1), (0, 1, 1, 1), (1, 0, 1, 1)])
            root.automatic = False
            root.sync()
            runtime.flush()
            runtime.snapshot()
            self.assertEqual(len(root.grid.ui.children), 1)
            self.assertEqual(root.grid.ui.children[0].node.text, 'manual')
        finally:
            runtime.close()
