"""Shared optional-model checks against native desktop Tabs adapters."""


class TabsNativeCases:
    def create(self, model=None, specs=(('alpha', 'Alpha'), ('', 'Beta'))):
        backend = self.backend
        edit = backend.DummyBinding('draft')

        class Example(backend.Application):
            binding = model
            pages = list(specs)

            def content(self):
                with backend.Window(size=(640, 400)):
                    with backend.Tabs(model=self.binding).ref('test.tabs'):
                        for key, label in self.pages:
                            with backend.Tab(label).id(key):
                                backend.TextField(edit)

        self.mount(Example())
        return self.tabs()

    def test_binder_select_from_worker(self):
        import time
        from ref_thread_helpers import call_in_thread
        node = self.create()
        binder = self.backend.ref('test.tabs')
        self.assertIs(binder.node, node)
        self.assertFalse(hasattr(node, 'select'))
        call_in_thread(lambda: binder.select('Beta'))
        self.assertEqual(node.model.value, 'alpha')
        deadline = time.monotonic() + 2
        while self.selected_index() != 1 and time.monotonic() < deadline:
            self.pump()
            time.sleep(0.005)
        self.assertEqual(self.tabs().model.value, 'Beta')
        self.assertEqual(self.selected_index(), 1)

    def tabs(self):
        return self.root.children[0].children[0]

    def test_internal_select_native_selection_and_old_handle(self):
        old = self.create()
        internal = old.model
        self.assertEqual(self.selected_index(), 0)
        self.assertEqual(internal.value, 'alpha')
        old._select('Beta')
        self.pump()
        self.assertEqual(self.selected_index(), 1)
        self.native_select(0)
        self.pump()
        self.assertEqual(internal.value, 'alpha')
        self.sync()
        self.assertIs(self.tabs().model, internal)
        old._select('Beta')
        self.pump()
        self.assertEqual(self.selected_index(), 1)

    def test_state_and_native_selection_share_model(self):
        state = self.backend.State()
        state.selection = 'Beta'
        old = self.create(state('selection'))
        self.assertEqual(self.selected_index(), 1)
        state.selection = 'alpha'
        self.pump()
        self.assertEqual(self.selected_index(), 0)
        self.native_select(1)
        self.pump()
        self.assertEqual(state.selection, 'Beta')
        old._select('alpha')
        self.pump()
        self.assertEqual(state.selection, 'alpha')

    def test_first_match_and_explicit_id_overrides_label(self):
        old = self.create(specs=(('dup', 'first'), ('dup', 'second'), ('', 'same'), ('', 'same')))
        old._select('dup')
        self.pump()
        self.assertEqual(self.selected_index(), 0)
        old._select('same')
        self.pump()
        self.assertEqual(self.selected_index(), 2)
        self.native_select(3)
        self.pump()
        self.assertEqual(self.selected_index(), 2)
        self.assertEqual(self.tabs().model.value, 'same')
        old._select('second')  # Explicit ID wins; the label is not another alias.
        self.pump()
        self.assertEqual(self.selected_index(), 0)
        self.assertEqual(self.tabs().model.value, 'second')

    def test_reorder_rename_empty_reappearance_and_model_rebinding(self):
        first = self.backend.DummyBinding('alpha')
        old = self.create(first)
        native_page = old.children[0].outer
        self.root.pages = [('', 'Beta'), ('alpha', 'Renamed')]
        self.sync()
        self.assertEqual(self.selected_index(), 1)
        self.assertIs(self.tabs().children[1].outer, native_page)
        self.assertEqual(self.tab_label(1), 'Renamed')
        second = self.backend.DummyBinding('Beta')
        self.root.binding = second
        self.sync()
        old._select('alpha')
        self.pump()
        self.assertEqual(second.value, 'alpha')
        self.assertEqual(first.value, 'alpha')
        for pages, index in [([], None), ([('', 'Beta')], 0), ([('', 'Beta'), ('alpha', 'Renamed')], 1)]:
            self.root.pages = pages
            self.sync()
            self.assertEqual(self.selected_index(), index)
            self.assertEqual(second.value, 'alpha')
        old._select(None)
        self.pump()
        self.assertEqual(self.selected_index(), 0)
        self.assertIsNone(second.value)
