"""env/bin/python -m unittest discover -s tests -p textual_views.py -v"""
import contextlib
import io
import unittest

from PUI.textual import Application, Window, PUIView, Views, Label, TextField, State
from PUI.dom import recur_delete


class Editor(PUIView):
    def setup(self):
        self.state = State()
        self.state.text = 'initial'

    def content(self):
        Label('Editor')
        TextField(self.state('text'))


class Example(Application):
    order = ['editor', 'other page']

    def __init__(self, model=None):
        super().__init__()
        self.binding = model

    def content(self):
        with Window():
            with Views(self.binding) as self.views:
                for key in self.order:
                    Editor().id(key)


class TextualViewsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.root = None
        self.output = io.StringIO()
        self.stdout = contextlib.redirect_stdout(self.output)
        self.stderr = contextlib.redirect_stderr(self.output)
        self.stdout.__enter__()
        self.stderr.__enter__()

    async def asyncTearDown(self):
        self.stderr.__exit__(None, None, None)
        self.stdout.__exit__(None, None, None)
        self.assertNotIn('<ERROR', self.output.getvalue(), self.output.getvalue())

    def selected(self):
        views = self.root.views
        visible = [page._id for page in views.children if page.ui.display]
        self.assertLessEqual(len(visible), 1)
        self.assertEqual(views.ui.visible_content,
                         next((p.ui for p in views.children if p.ui.display), None))
        return visible[0] if visible else None

    async def test_internal_selection_old_handles_and_removed_container(self):
        self.root = Example()
        async with self.root.ui.run_test() as pilot:
            await pilot.pause()
            old = self.root.views
            model = old.model
            self.assertIsNone(self.selected())
            old._select('other page')
            await pilot.pause()
            self.assertEqual(self.selected(), 'other page')
            self.root.redraw()
            await pilot.pause()
            self.assertIs(self.root.views.model, model)
            old._select('editor')
            await pilot.pause()
            self.assertEqual(self.selected(), 'editor')
            old._select(None)
            await pilot.pause()
            self.assertIsNone(self.selected())
            recur_delete(self.root, self.root.views, True)
            old._select('editor')
            await pilot.pause()
            self.assertIsNone(model.value)

    async def test_state_selection_rebinding_missing_and_reappearing_page(self):
        state = State()
        state.selection = 'editor'
        self.root = Example(state('selection'))
        async with self.root.ui.run_test() as pilot:
            await pilot.pause()
            old = self.root.views
            for order, expected in [([], None), (['other page'], None), (['other page', 'editor'], 'editor')]:
                self.root.order = order
                self.root.redraw()
                await pilot.pause()
                self.assertEqual(self.selected(), expected)
                self.assertEqual(state.selection, 'editor')
            old._select(None)
            await pilot.pause()
            self.assertIsNone(state.selection)
            self.assertIsNone(self.selected())
            other = State()
            other.selection = 'other page'
            self.root.binding = other('selection')
            self.root.redraw()
            await pilot.pause()
            self.assertEqual(self.selected(), 'other page')
            old._select('editor')
            await pilot.pause()
            self.assertEqual(other.selection, 'editor')
            self.assertIsNone(state.selection)

    async def test_native_typing_survives_switch_reorder_and_independent_redraw(self):
        self.root = Example()
        async with self.root.ui.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            self.root.views._select('editor')
            await pilot.pause()
            editor = self.root.views.children[0].children[0]
            field = editor.children[1].ui
            field.focus()
            await pilot.press('end', 'x', 'y')
            await pilot.pause()
            draft = field.value
            self.assertEqual(draft, 'initialxy')
            self.root.views._select('other page')
            await pilot.pause()
            self.root.views._select('editor')
            await pilot.pause()
            self.root.order = ['other page', 'editor']
            self.root.redraw()
            await pilot.pause()
            self.assertIs(self.root.views.children[1].children[0], editor)
            self.assertIs(editor.children[1].ui, field)
            self.assertEqual(list(self.root.views.ui.children), [p.ui for p in self.root.views.children])
            self.assertEqual(field.value, draft)
            editor.redraw()
            await pilot.pause()
            self.assertEqual(field.value, draft)
            field.focus()
            await pilot.press('enter')
            await pilot.pause()
            self.assertEqual(editor.state.text, draft)
            self.root.order = ['editor']
            self.root.redraw()
            await pilot.pause()
            self.assertEqual(len(self.root.views.ui.children), 1)
            self.assertEqual(self.selected(), 'editor')


if __name__ == '__main__':
    unittest.main()
