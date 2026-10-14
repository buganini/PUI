"""Table edits preserve types and cannot target moved/rebound data."""
import asyncio
import unittest

from PUI.web import Application, Window, Table, TableNode, State, BaseTableAdapter
from PUI.web.runtime import Runtime


class Adapter(BaseTableAdapter):
    def __init__(self):
        self.values = [[1, True]]
    def rowCount(self): return len(self.values)
    def columnCount(self): return 2
    def data(self, row, col): return self.values[row][col]
    def editable(self, row, col): return True
    def setData(self, row, col, value): self.values[row][col] = value


class App(Application):
    def setup(self):
        self.state = State()
        self.state.number, self.state.choice = 3, None
        self.state.items = ['a', 'b']
        self.adapter = Adapter()
        self.reverse = False
        self.calls = []

    def content(self):
        with Window():
            with Table(columnHeader=['value']).id('nodes'):
                for key in (['choice', 'number'] if self.reverse else ['number', 'choice']):
                    with TableNode().id(key):
                        TableNode(self.state(key), choices=[None, True, 7] if key == 'choice' else None).id('value').click(
                            lambda e: self.calls.append('click'))
                with TableNode().id('list'):
                    TableNode(self.state.items(0))
            Table(self.adapter).id('adapter')


class TableTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = App()
        self.refresh()

    async def asyncTearDown(self):
        self.runtime.close()

    def refresh(self):
        self.runtime.app.sync()
        self.runtime.flush()
        return self.runtime.snapshot()

    def node(self, key='nodes'):
        return next(e.node for e in self.runtime.nodes.values() if e.node._id == key)

    def event(self, row, value=None, action='commit', seq=1, key='nodes'):
        node = self.node(key)
        token = node.properties()['rows'][row]['cells'][0]['token']
        return dict(node_id=node.ui.id, event='table', token=node.ui.events['table'], observed_render_rev=1,
                    data=dict(cell=token, action=action, value=value, edit_seq=seq))

    def test_number_validation_choices_and_callback(self):
        body = self.event(0, 'invalid')
        self.assertEqual(self.runtime.action('event', body)[0], 'processed')
        self.assertEqual(self.runtime.app.state.number, 3)
        self.assertTrue(self.node().properties()['rows'][0]['cells'][0]['error'])
        body['data'].update(value='42', edit_seq=2)
        self.assertEqual(self.runtime.action('event', body)[0], 'processed')
        self.runtime.flush(); self.runtime.snapshot()
        self.assertEqual(self.runtime.app.state.number, 42)
        self.assertEqual(self.runtime.action('event', body)[0], 'stale')
        for index, expected in ((1, True), (2, 7), (0, None)):
            self.assertEqual(self.runtime.action('event', self.event(1, index))[0], 'processed')
            self.runtime.flush(); self.runtime.snapshot()
            self.assertIs(type(self.runtime.app.state.choice), type(expected))
            self.assertEqual(self.runtime.app.state.choice, expected)
        self.runtime.action('event', self.event(0, action='click'))
        self.assertEqual(self.runtime.app.calls, ['click'])

    def test_keyed_moves_retain_token_but_source_changes_revoke(self):
        body = self.event(0, '8')
        self.runtime.app.reverse = True
        self.refresh()
        self.assertEqual(self.event(1, '8')['data']['cell'], body['data']['cell'])
        self.assertEqual(self.runtime.action('event', body)[0], 'processed')
        self.runtime.flush(); self.runtime.snapshot()
        stale = self.event(1, '9')
        self.runtime.app.state.number = 10
        self.assertEqual(self.runtime.action('event', stale)[0], 'stale')
        self.assertEqual(self.runtime.app.state.number, 10)

    def test_list_structure_invalidates_even_before_redraw(self):
        body = self.event(2, 'wrong')
        self.runtime.app.state.items.reverse()
        self.assertEqual(self.runtime.action('event', body)[0], 'stale')
        self.assertEqual(list(self.runtime.app.state.items), ['b', 'a'])

    def test_adapter_edit_and_reconciliation_cancels_old_target(self):
        body = self.event(0, '7', key='adapter')
        self.assertEqual(self.runtime.action('event', body)[0], 'processed')
        self.assertEqual(self.runtime.app.adapter.values[0][0], 7)
        self.refresh()
        body = self.event(0, '9', key='adapter')
        self.refresh()
        self.assertEqual(self.runtime.action('event', body)[0], 'stale')

    def test_reset_connection_and_invalid_event(self):
        body = self.event(0, '7')
        self.runtime.reset_connection(); self.runtime.snapshot()
        self.assertEqual(self.runtime.action('event', body)[0], 'stale')
        body = self.event(0, '7'); body['data']['action'] = 'delete'
        self.assertEqual(self.runtime.action('event', body)[0], 'invalid')
