"""Shared model and reconciliation checks for async Tabs backends."""


class TabsAsyncCases:
    async def create(self, model=None, specs=(('alpha', 'Alpha'), ('', 'Beta'))):
        backend = self.backend
        edit = backend.DummyBinding('draft')

        class Example(backend.Application):
            binding = model
            pages = list(specs)

            def content(self):
                with backend.Window():
                    with backend.Tabs(model=self.binding).ref('test.tabs'):
                        for key, label in self.pages:
                            with backend.Tab(label).id(key):
                                backend.TextField(edit)

        await self.mount(Example())
        return self.tabs()

    async def test_binder_select_from_worker(self):
        from ref_thread_helpers import call_in_thread
        node = await self.create()
        binder = self.backend.ref('test.tabs')
        self.assertIs(binder.node, node)
        self.assertFalse(hasattr(node, 'select'))
        call_in_thread(lambda: binder.select('Beta'))
        self.assertEqual(node.model.value, 'alpha')
        await self.pump()
        await self.pump()
        self.assertEqual(self.tabs().model.value, 'Beta')
        self.assertEqual(self.selected_index(), 1)

    def tabs(self):
        return self.root.children[0].children[0]

    async def test_internal_select_and_native_selection(self):
        old = await self.create()
        model = old.model
        self.assertEqual(self.selected_index(), 0)
        self.assertEqual(model.value, 'alpha')
        old._select('Beta')
        await self.pump()
        self.assertEqual(self.selected_index(), 1)
        await self.native_select(0)
        self.assertEqual(model.value, 'alpha')
        self.root.redraw()
        await self.pump()
        self.assertIs(self.tabs().model, model)
        old._select('Beta')
        await self.pump()
        self.assertEqual(self.selected_index(), 1)

    async def test_state_and_native_selection(self):
        state = self.backend.State()
        state.selection = 'Beta'
        old = await self.create(state('selection'))
        self.assertEqual(self.selected_index(), 1)
        state.selection = 'alpha'
        await self.pump()
        self.assertEqual(self.selected_index(), 0)
        await self.native_select(1)
        self.assertEqual(state.selection, 'Beta')
        old._select('alpha')
        await self.pump()
        self.assertEqual(state.selection, 'alpha')

    async def test_duplicate_ids_and_labels_select_first_match(self):
        old = await self.create(specs=(('dup', 'first'), ('dup', 'second'), ('', 'same'), ('', 'same')))
        old._select('dup')
        await self.pump()
        self.assertEqual(self.selected_index(), 0)
        old._select('same')
        await self.pump()
        self.assertEqual(self.selected_index(), 2)
        await self.native_select(3)
        self.assertEqual(self.selected_index(), 2)
        old._select('second')
        await self.pump()
        self.assertEqual(self.selected_index(), 0)
        self.assertEqual(self.tabs().model.value, 'second')

    async def test_retained_pages_reorder_rename_empty_and_rebind(self):
        state = self.backend.DummyBinding('alpha')
        old = await self.create(state)
        native = old.children[0].outer
        self.root.pages = [('', 'Beta'), ('alpha', 'Renamed')]
        self.root.redraw()
        await self.pump()
        self.assertEqual(self.selected_index(), 1)
        self.assertIs(self.tabs().children[1].outer, native)
        self.assertEqual(self.tab_label(1), 'Renamed')
        second = self.backend.DummyBinding('Beta')
        self.root.binding = second
        self.root.redraw()
        await self.pump()
        old._select('alpha')
        await self.pump()
        self.assertEqual(second.value, 'alpha')
        for pages, index in [([], None), ([('', 'Beta')], 0), ([('', 'Beta'), ('alpha', 'Renamed')], 1)]:
            self.root.pages = pages
            self.root.redraw()
            await self.pump()
            self.assertEqual(self.selected_index(), index)
            self.assertEqual(second.value, 'alpha')
        old._select(None)
        await self.pump()
        self.assertIsNone(second.value)
        self.assertEqual(self.selected_index(), 0)
