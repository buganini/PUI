"""Declarative visibility uses ordinary State reads and retains browser elements."""
import asyncio
import unittest
from PUI.web import Application, Window, VBox, Label, State, PUIView
from PUI.web.runtime import Runtime


class VisibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_hidden_subtree_is_lazy_retained_and_refreshed(self):
        created = []
        shared = State()
        shared.value = 'initial'
        class Inner(PUIView):
            def setup(self):
                created.append(self)
            def content(self):
                Label(shared.value)
        class Child(PUIView):
            def content(self):
                with VBox():
                    Inner()
        class Example(Application):
            def setup(self):
                self.state = State()
                self.state.shown = False
                self.state.present = True
            def content(self):
                with Window():
                    if self.state.present:
                        with VBox().visible(self.state.shown):
                            Child()
                    Label('after')
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            runtime.flush()
            app = runtime.app
            self.assertEqual(created, [])
            self.assertEqual(app.children[0].children[0].children, [])
            app.state.shown = True
            runtime.flush()
            inner = created[0]
            label_ui = inner.children[0].ui
            app.state.shown = False
            runtime.flush()
            shared.value = 'latest'
            runtime.flush()
            self.assertEqual(inner.children[0].text, 'initial')
            self.assertFalse(inner.updating)
            app.state.shown = True
            runtime.flush()
            self.assertEqual(inner.children[0].text, 'latest')
            self.assertIs(inner.children[0].ui, label_ui)
            self.assertEqual(len(created), 1)
            app.pui_frozen = True
            shared.value = 'direct freeze'
            runtime.flush()
            self.assertEqual(inner.children[0].text, 'latest')
            app.pui_frozen = False
            app.sync()
            runtime.flush()
            self.assertEqual(inner.children[0].text, 'direct freeze')
            app.state.shown = False
            runtime.flush()
            app.state.present = False
            runtime.flush()
            self.assertTrue(inner.destroyed)
            self.assertEqual(runtime.snapshot()['roots'][0]['children'][0]['props']['text'], 'after')
        finally:
            runtime.close()

    async def test_explicit_frozen_view_and_unmounted_proposal_cleanup(self):
        from PUI.view import PUIView as BaseView
        from PUI.dom import recur_delete
        calls = []
        class Child(PUIView):
            def setup(self):
                calls.append('setup')
            def content(self):
                calls.append('content')
                Label('value')
        class Example(Application):
            frozen = True
            def content(self):
                with Window():
                    child = Child()
                    child.pui_frozen = self.frozen
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            self.assertEqual(calls, [])
            runtime.app.frozen = False
            runtime.app.sync()
            runtime.flush()
            self.assertEqual(calls, ['setup', 'content'])
            child = runtime.app.children[0].children[0]
            runtime.app.frozen = True
            runtime.app.sync()
            child.redraw()
            runtime.flush()
            self.assertEqual(calls, ['setup', 'content'])
            runtime.app.frozen = False
            runtime.app.sync()
            runtime.flush()
            self.assertEqual(calls, ['setup', 'content', 'content'])
            # Newly constructed children under an initially hidden node must
            # not remain registered as live views.
            before = set(BaseView.__ALLVIEWS__)
            class Hidden(Application):
                def content(self):
                    with Window():
                        with VBox().visible(False):
                            Child()
            hidden = Hidden()
            hidden.sync()
            self.assertEqual(set(BaseView.__ALLVIEWS__) - before, {hidden})
            recur_delete(hidden, hidden, True)
        finally:
            runtime.close()

    async def test_state_read_updates_visibility_without_replacing_element(self):
        class Example(Application):
            def setup(self):
                self.state = State()
                self.state.show = True
            def content(self):
                with Window():
                    with VBox():
                        Label('Toggle').visible(self.state.show)
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app = Example()
            runtime.app.sync()
            runtime.flush()
            label = runtime.app.children[0].children[0].children[0]
            element = label.ui
            for shown in (False, True, False):
                runtime.app.state.show = shown
                runtime.flush()
                snapshot = runtime.snapshot()
                label = runtime.app.children[0].children[0].children[0]
                self.assertIs(label.ui, element)
                wire = snapshot['roots'][0]['children'][0]['children'][0]
                self.assertEqual(wire['layout'].get('visible', True), shown)
        finally:
            runtime.close()
