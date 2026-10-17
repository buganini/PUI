import asyncio
import unittest
from PUI.web import Application, PUIView, Window, Label, TextField, State, Views, Tabs, Tab
from PUI.web.runtime import Runtime


class Editor(PUIView):
    def setup(self):
        self.state = State()
        self.state.text = 'retained'

    def content(self):
        TextField(self.state('text'))


class App(Application):
    def setup(self):
        self.selection = State()
        self.selection.key = 'editor'
        self.pages = ['editor', 'settings']
        self.external = False

    def content(self):
        with Window():
            with Views(model=self.selection('key') if self.external else None) .ref('test.views') as self.views:
                for key in self.pages:
                    if key == 'editor':
                        Editor().id(key)
                    else:
                        Label(key).id(key)
            with Tabs(model=self.selection('key') if self.external else None) as self.tabs:
                for key in self.pages:
                    with Tab('Editor' if key == 'editor' else 'Settings').id(key):
                        Label(key)


class SelectionTests(unittest.IsolatedAsyncioTestCase):
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

    def selected(self, container):
        return next((child._id for child in container.children if child.ui.id == container.selected), None)

    def action(self):
        tabs = self.runtime.app.tabs
        return {'node_id': tabs.ui.id, 'event': 'select', 'token': tabs.ui.events['select'],
                'observed_render_rev': 1, 'data': {'page_id': tabs.children[-1].ui.id}}

    async def test_binder_select_tracks_reconciliation_and_drops_removed_work(self):
        from PUI import ref
        from ref_thread_helpers import call_in_thread
        binder = ref('test.views')
        old = binder.node
        self.assertFalse(hasattr(old, 'select'))
        call_in_thread(lambda: binder.select('editor'))
        self.assertIsNone(old.model.value)
        self.refresh()
        self.assertIs(binder.node, old)
        self.assertIs(binder.node.get_node(), self.runtime.app.views)
        await asyncio.sleep(0)
        self.runtime.flush()
        self.assertEqual(self.selected(self.runtime.app.views), 'editor')
        binder.select('settings')
        self.runtime.close()
        await asyncio.sleep(0)
        with self.assertRaises(RuntimeError):
            binder.select('editor')
        self.assertTrue(binder.node.get_node().destroyed)

    def test_optional_models_and_old_handles_retain_pages(self):
        app = self.runtime.app
        self.assertIsNone(self.selected(app.views))
        self.assertEqual(self.selected(app.tabs), 'editor')
        old, editor = app.views, app.views.children[0].children[0]
        old._select('editor')
        self.refresh()
        self.assertEqual(self.selected(app.views), 'editor')
        old._select('settings')
        self.refresh()
        old._select('editor')
        self.refresh()
        self.assertIs(app.views.children[0].children[0], editor)
        old._select(None)
        self.refresh()
        self.assertIsNone(self.selected(app.views))
        app.tabs._select('settings')
        self.refresh()
        self.assertEqual(self.selected(app.tabs), 'settings')

    def test_native_selection_model_rebinding_and_stale_pages(self):
        old = self.action()
        self.runtime.app.external = True
        self.refresh()
        self.assertEqual(self.runtime.action('event', old)[0], 'stale')
        current = self.action()
        self.assertEqual(self.runtime.action('event', current)[0], 'processed')
        self.runtime.flush()
        self.runtime.snapshot()
        self.assertEqual(self.runtime.app.selection.key, 'settings')
        self.assertEqual(self.selected(self.runtime.app.views), 'settings')
        self.runtime.app.pages = ['editor']
        self.refresh()
        self.assertEqual(self.runtime.action('event', current)[0], 'stale')
        self.assertIsNone(self.selected(self.runtime.app.views))
        self.assertEqual(self.selected(self.runtime.app.tabs), 'editor')
        self.assertEqual(self.runtime.app.selection.key, 'settings')

    def test_reorder_and_empty_containers_release_registrations(self):
        app = self.runtime.app
        editor = app.views.children[0].children[0]
        app.pages.reverse()
        self.refresh()
        self.assertIs(app.views.children[1].children[0], editor)
        app.pages = []
        tree = self.refresh()
        self.assertIsNone(self.selected(app.views))
        self.assertIsNone(self.selected(app.tabs))
        self.assertEqual(len(tree['bindings']), 1)  # only Tabs' internal model

    async def test_tabs_fallback_ids_and_duplicate_first_match(self):
        class Duplicate(Application):
            def content(self):
                with Window():
                    with Tabs() as self.tabs:
                        with Tab('same'):
                            Label('first')
                        with Tab('same'):
                            Label('second')
                        with Tab('named').id('explicit'):
                            Label('third')
        self.runtime.close()
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = Duplicate()
        self.refresh()
        app = self.runtime.app
        self.assertEqual(app.tabs.model.value, 'same')
        app.tabs._select('explicit')
        self.refresh()
        self.assertEqual(app.tabs.selected, app.tabs.children[2].ui.id)
        event = self.action()  # deliberately select the second duplicate by native ID
        event['data']['page_id'] = app.tabs.children[1].ui.id
        self.assertEqual(self.runtime.action('event', event)[0], 'processed')
        self.runtime.flush()
        self.assertEqual(app.tabs.selected, app.tabs.children[0].ui.id)
