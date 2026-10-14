"""Basic widget validation and server-side disabled-event enforcement."""
import asyncio
import unittest
from PUI.web import Application, Window, VBox, Label
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
        with self.assertRaisesRegex(NotImplementedError, 'grid'):
            self.runtime.snapshot()

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
