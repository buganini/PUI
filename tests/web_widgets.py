"""Basic widget validation and server-side disabled-event enforcement."""
import asyncio
import unittest
from PUI.web import Application, Window, VBox, Label, Grid, Stack, ProgressBar, Scroll
from PUI.web.runtime import Runtime
from web_fixture import App


class WidgetTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = App()
        self.runtime.app.sync()
        self.runtime.snapshot()
        self.button = next(e for e in self.runtime.nodes.values() if e.node.wire_type == 'Button')

    async def asyncTearDown(self):
        self.runtime.close()

    def test_disabled_button_rejects_stale_click_and_can_be_reenabled(self):
        body = {'node_id': self.button.id, 'event': 'click', 'token': self.button.events['click'],
                'observed_render_rev': 1, 'data': {}}
        self.button.node.enabled = False
        self.runtime.snapshot()
        self.assertEqual(self.runtime.action('event', body, render_rev=2)[0], 'stale')
        self.assertEqual(self.runtime.app.state.count, 0)
        self.button.node.enabled = True
        self.assertEqual(self.runtime.action('event', body, render_rev=2)[0], 'processed')
        self.assertEqual(self.runtime.app.state.count, 1)

    def test_invalid_styles_and_dimensions_fail_before_publication(self):
        for attribute, value in (
            ('layout_width', -1), ('layout_height', float('inf')), ('layout_weight', True),
            ('layout_padding', (0, -1, 0, 0)), ('layout_margin', (0, 0, float('nan'), 0)),
            ('style_fontsize', -3), ('style_fontweight', 1001), ('style_fontweight', 'heavy'),
            ('style_fontfamily', []), ('style_color', 'red'),
        ):
            with self.subTest(attribute=attribute, value=value):
                setattr(self.button.node, attribute, value)
                try:
                    with self.assertRaises(ValueError):
                        self.runtime.snapshot()
                finally:
                    setattr(self.button.node, attribute, None)

    def test_unsupported_handlers_and_grid_are_explicit(self):
        for method in ('dblclick', 'keypress', 'mousedown', 'mouseup', 'mousemove',
                       'mouseenter', 'mouseleave', 'wheel', 'dragEnter', 'drop', 'input', 'change'):
            with self.subTest(method=method):
                self.runtime.app.sync()
                self.runtime.snapshot()
                node = next(e.node for e in self.runtime.nodes.values() if e.node.wire_type == 'Button')
                getattr(node, method)(lambda event: None)
                with self.assertRaisesRegex(NotImplementedError, method):
                    self.runtime.snapshot()
        self.runtime.app.sync()
        self.runtime.snapshot()
        node = next(e.node for e in self.runtime.nodes.values() if e.node.wire_type == 'Button')
        node.grid(row=0, column=0)
        with self.assertRaisesRegex(ValueError, 'Grid'):
            self.runtime.snapshot()

    async def test_grid_placement_and_progress_properties(self):
        class LayoutApp(Application):
            def content(self):
                with Window():
                    with Grid():
                        Label('left').id('left').grid(row=0, column=0)
                        Label('span').id('span').grid(row=0, column=1, rowspan=2)
                        Label('bottom').grid(row=1, column=0)
                    ProgressBar(25, 100)
                    ProgressBar(2)
                    ProgressBar(-1)
                    ProgressBar(0, 0)
        self.runtime.close()
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = LayoutApp()
        self.runtime.app.sync()
        tree = self.runtime.snapshot()['roots'][0]
        grid = tree['children'][0]
        self.assertEqual(grid['type'], 'Grid')
        self.assertEqual(grid['children'][1]['layout'], {'row': 0, 'column': 1, 'rowspan': 2})
        self.assertEqual([n['props']['progress'] for n in tree['children'][1:]], [25, 1, 0, 0])
        child = next(e.node for e in self.runtime.nodes.values() if e.node._id == 'span')
        child.grid_rowspan = 0
        with self.assertRaisesRegex(ValueError, 'grid'):
            self.runtime.snapshot()

    async def test_stack_keeps_declaration_order_and_keyed_children(self):
        class StackApp(Application):
            def setup(self):
                self.labels = ['bottom', 'top']

            def content(self):
                with Window():
                    with Stack():
                        for text in self.labels:
                            Label(text).id(text)
        self.runtime.close()
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = StackApp()
        self.runtime.app.sync()
        stack = self.runtime.snapshot()['roots'][0]['children'][0]
        self.assertEqual(stack['type'], 'Stack')
        self.assertEqual([n['props']['text'] for n in stack['children']], ['bottom', 'top'])
        ids = [n['id'] for n in stack['children']]
        self.runtime.app.labels.reverse()
        self.runtime.app.sync()
        stack = self.runtime.snapshot()['roots'][0]['children'][0]
        self.assertEqual([n['id'] for n in stack['children']], ids[::-1])

    async def test_scroll_requests_preserve_declarations_and_follow_old_handles(self):
        class ScrollApp(Application):
            def content(self):
                with Window():
                    with Scroll().scrollY(Scroll.END) as self.scroll:
                        Label('content')
        self.runtime.close()
        self.runtime = Runtime(asyncio.get_running_loop())
        self.runtime.app = ScrollApp()
        self.runtime.app.sync()
        old = self.runtime.app.scroll
        self.assertEqual(old.properties()['scroll_y'], ['end', 0, 1])
        self.runtime.app.sync()
        current = self.runtime.app.scroll
        self.assertEqual(current.properties()['scroll_y'], ['end', 0, 1])
        old.scrollY(-12)
        self.assertEqual(current.properties()['scroll_y'], ['end', 12, 2])
        self.runtime.app.sync()
        self.assertEqual(self.runtime.app.scroll.properties()['scroll_y'], ['end', 12, 2])
        old.scrollY(-12)
        self.assertEqual(self.runtime.app.scroll.properties()['scroll_y'], ['end', 12, 3])
        old.scrollX(20)
        self.assertEqual(self.runtime.app.scroll.properties()['scroll_x'], ['start', 20, 1])

    async def test_invalid_window_roots_are_explicit(self):
        class Multiple(Application):
            def content(self):
                Window('one')
                Window('two')
        class Nested(Application):
            def content(self):
                with Window():
                    with VBox():
                        Window('nested')
        class Missing(Application):
            def content(self):
                Label('no Window')
        for application in (Multiple, Nested, Missing):
            with self.subTest(application=application):
                self.runtime.close()
                self.runtime = Runtime(asyncio.get_running_loop())
                self.runtime.app = application()
                self.runtime.app.sync()
                with self.assertRaisesRegex(NotImplementedError, 'Window'):
                    self.runtime.snapshot()
