"""QT_QPA_PLATFORM=offscreen env/bin/python -m unittest discover -s tests -p pyside6_views.py -v"""
import contextlib
import io
import unittest

from PySide6 import QtWidgets, QtCore
from PUI.PySide6 import Application, PUIView, Window, Views, VBox, TextField, Label, State, DummyBinding
from PUI.dom import recur_delete


class PySideViewsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.root = None

    def tearDown(self):
        if self.root:
            self.root.ui = None  # The QApplication belongs to the test harness.
            recur_delete(self.root, self.root, True)
        for widget in self.app.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.root.sync()
        self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())
        self.app.processEvents()

    def mount(self, root):
        self.root = root
        root.ui = self.app
        self.sync()
        return root.children[0].children[0]

    def test_internal_model_selection_survives_redraw_and_old_handles(self):
        class Example(Application):
            def content(self):
                with Window():
                    with Views():
                        Label('editor').id('editor')
                        Label('settings').id('settings')
        original = self.mount(Example())
        self.assertEqual(original.ui.currentIndex(), 0)
        original.select('settings')
        self.app.processEvents()
        current = self.root.children[0].children[0]
        self.assertEqual(current.ui.currentIndex(), 2)
        self.sync()
        original.select('editor')
        self.app.processEvents()
        current = self.root.children[0].children[0]
        self.assertEqual(current.ui.currentIndex(), 1)
        self.assertIs(current.model, original.model)
        original.select(None)
        self.app.processEvents()
        self.assertEqual(current.get_node().ui.currentIndex(), 0)

    def test_binding_changes_and_select_write_to_model(self):
        state = State()
        state.page = 'b'
        class Example(Application):
            def content(self):
                with Window():
                    with Views(state('page')):
                        Label('a').id('a')
                        Label('b').id('b')
        views = self.mount(Example())
        self.assertEqual(views.get_node().ui.currentIndex(), 2)
        state.page = 'a'
        self.app.processEvents()
        self.assertEqual(views.get_node().ui.currentIndex(), 1)
        views.select('b')
        self.app.processEvents()
        self.assertEqual(state.page, 'b')
        self.assertEqual(views.get_node().ui.currentIndex(), 2)

    def test_virtual_views_keep_instances_and_edits_through_switches_and_moves(self):
        edits = {key: DummyBinding(key) for key in 'abc'}
        selection = DummyBinding('a')
        class Editor(PUIView):
            def __init__(self, key):
                super().__init__()
                self.editor_key = key
                self.local_state = 0
            def content(self):
                Label(self.editor_key)
                TextField(edits[self.editor_key])
        class Example(Application):
            order = list('abc')
            def content(self):
                with Window():
                    with Views(selection):
                        for key in self.order:
                            Editor(key).id(key)
        views = self.mount(Example())
        editors = {p._id: p.children[0] for p in views.children}
        editor = editors['a']
        editor.local_state = 42
        field = editor.children[1].ui
        field.setText('draft')
        views.select('b')
        self.app.processEvents()
        views.select('a')
        self.app.processEvents()
        self.root.order = list('ca')
        self.sync()
        views = self.root.children[0].children[0]
        self.assertIs(views.children[1].children[0], editor)
        self.assertIs(editor.children[1].ui, field)
        self.assertEqual(editor.local_state, 42)
        self.assertEqual(field.text(), 'draft')
        self.assertEqual(views.get_node().ui.currentIndex(), 2)
        self.assertTrue(editors['b'].destroyed)
        editor.redraw()
        self.app.processEvents()
        self.assertEqual(field.text(), 'draft')

    def test_missing_selection_removal_empty_and_reappearance(self):
        model = DummyBinding('a')
        class Example(Application):
            keys = ['a']
            def content(self):
                with Window():
                    with Views(model):
                        for key in self.keys:
                            Label(key).id(key)
        views = self.mount(Example())
        for keys, index in (([], 0), (['b'], 0), (['b', 'a'], 2)):
            self.root.keys = keys
            self.sync()
            self.assertEqual(views.get_node().ui.currentIndex(), index)
            self.assertEqual(model.value, 'a')
        views.select('unknown')
        self.app.processEvents()
        self.assertEqual(views.get_node().ui.currentIndex(), 0)

    def test_duplicate_and_missing_ids_are_rejected(self):
        for keys in ([''], ['a', 'a']):
            view = PUIView()
            with self.assertRaises(ValueError):
                with view:
                    with Views():
                        for key in keys:
                            Label('page').id(key)
            recur_delete(view, view, True)
        with self.assertRaises(TypeError):
            Views('not-a-binding')


if __name__ == '__main__':
    unittest.main()
