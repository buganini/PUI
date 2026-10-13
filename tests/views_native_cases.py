"""Common behavior checks used by native Views backend harnesses."""


class ViewsNativeCases:
    def create(self, model=None, keys=('a', 'b', 'c')):
        backend = self.backend
        models = {key: backend.DummyBinding(key) for key in keys}

        class Editor(backend.PUIView):
            def __init__(self, key):
                super().__init__()
                self.editor_key = key
                self.local_state = 0

            def content(self):
                backend.Label(self.editor_key)
                backend.TextField(models[self.editor_key])

        class Example(backend.Application):
            order = list(keys)
            binding = model

            def content(self):
                with backend.Window(size=(640, 400)):
                    with backend.Views(self.binding):
                        for key in self.order:
                            Editor(key).id(key)

        self.mount(Example())
        return self.views()

    def views(self):
        return self.root.children[0].children[0]

    def editor(self, key):
        page = next(p for p in self.views().children if p._id == key)
        while not isinstance(page, self.backend.PUIView):
            page = page.children[0]
        return page

    def test_internal_model_old_handle_and_empty_selection(self):
        old = self.create()
        internal = old.model
        self.assertIsNone(self.selected())
        old.select('b')
        self.pump()
        self.assertEqual(self.selected(), 'b')
        self.sync()
        self.assertIs(self.views().model, internal)
        old.select('a')
        self.pump()
        self.assertEqual(self.selected(), 'a')
        old.select(None)
        self.pump()
        self.assertIsNone(self.selected())

    def test_switch_reorder_and_remove_retain_view_state(self):
        old = self.create(self.backend.DummyBinding('a'))
        editor = self.editor('a')
        editor.local_state = 42
        field = editor.children[1].ui
        self.write_text(editor.children[1], 'draft')
        old.select('b')
        self.pump()
        old.select('a')
        self.pump()
        self.root.order = ['c', 'a']
        self.sync()
        self.assertEqual(self.selected(), 'a')
        self.assertIs(self.editor('a'), editor)
        self.assertIs(editor.children[1].ui, field)
        self.assertEqual(editor.local_state, 42)
        self.assertEqual(self.read_text(editor.children[1]), 'draft')
        editor.redraw()
        self.pump()
        self.assertEqual(self.read_text(editor.children[1]), 'draft')

    def test_missing_key_and_selected_removal_preserve_model(self):
        model = self.backend.DummyBinding('a')
        old = self.create(model)
        for order, selected in (([], None), (['b'], None), (['b', 'a'], 'a')):
            self.root.order = order
            self.sync()
            self.assertEqual(self.selected(), selected)
            self.assertEqual(model.value, 'a')
        old.select('unknown')
        self.pump()
        self.assertIsNone(self.selected())
        self.assertEqual(model.value, 'unknown')

    def test_binding_replacement_and_return_to_internal_model(self):
        first = self.backend.DummyBinding('a')
        old = self.create(first)
        second = self.backend.DummyBinding('b')
        self.root.binding = second
        self.sync()
        self.assertEqual(self.selected(), 'b')
        old.select('c')
        self.pump()
        self.assertEqual(second.value, 'c')
        self.assertEqual(first.value, 'a')
        self.root.binding = None
        self.sync()
        self.assertIsNone(self.selected())
        old.select('a')
        self.pump()
        self.assertEqual(self.selected(), 'a')
