"""env/bin/python -m unittest discover -s tests -p flet_regression.py"""
import asyncio
import contextlib
import io
import unittest
from pathlib import Path
import flet.canvas as cv
from types import SimpleNamespace

import flet as ft
import msgpack
from flet.messaging.connection import Connection
from flet.messaging.session import Session
from flet.messaging.protocol import configure_encode_object_for_msgpack
from flet.pubsub.pubsub_hub import PubSubHub
from PUI.flet import Application, Window, HBox, VBox, Label, Button, Checkbox, RadioButton, TextField, MaskedField, DummyBinding, Tabs, Tab, Scroll, ComboBox, ComboBoxItem, Canvas, Image, ProgressBar
from PUI.dom import recur_delete


class RecordingConnection(Connection):
    """Real Flet Session with a recording transport; no Flutter client simulated."""
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.pubsubhub = PubSubHub(loop=loop)
        self.messages = []
        self.encoder = configure_encode_object_for_msgpack(ft.BaseControl)

    def send_message(self, message):
        # Encoding captures Flet's snapshots used by subsequent control patches.
        msgpack.packb([message.action, message.body], default=self.encoder)
        self.messages.append(message)


class FletRegression(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connection = RecordingConnection(asyncio.get_running_loop())
        self.session = Session(self.connection)
        self.root = None

    async def asyncTearDown(self):
        if self.root is not None:
            recur_delete(self.root, self.root, True)
        await asyncio.sleep(0)

    async def mount(self, root):
        self.root = root
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            await root.flet_app(self.session.page)
        self.assertNotIn('<ERROR', output.getvalue())

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.root.sync()
        self.assertNotIn('<ERROR', output.getvalue())

    async def test_application_title_and_explicit_window_titles(self):
        class Example(Application):
            window_title = None
            def content(self):
                with Window(title=self.window_title):
                    Label('Title')
        await self.mount(Example(title='Application title'))
        for title in (None, 'Document', '', None):
            self.root.window_title = title
            self.sync()
            self.assertEqual(self.session.page.title, 'Application title' if title is None else title)

    async def test_placeholder_and_native_overrides_preserve_editor(self):
        await self.check_textfield(TextField)

    async def test_maskedfield_preserves_binding_and_edit_buffer(self):
        await self.check_textfield(MaskedField)

    async def check_textfield(self, field_type):
        model, edit = DummyBinding(''), DummyBinding('')
        events = []

        class Example(Application):
            options = {'placeholder': 'Enter text'}
            native_options = {}
            def content(self):
                with Window():
                    field_type(model, edit, 'Label', **self.options, **self.native_options).input(lambda e: events.append(('input', e.value))).change(lambda e: events.append(('change', e.value)))

        await self.mount(Example())
        native = self.root.children[0].children[0].ui
        self.assertEqual(native.password, field_type is MaskedField)
        self.assertEqual(native.hint_text, 'Enter text')
        self.assertEqual(native.label, 'Label')
        self.assertEqual((native.value, model.value, edit.value), ('', '', ''))
        self.assertEqual(events, [])
        native.value = 'typed'
        native.on_change(SimpleNamespace(control=native))
        for options, overrides in (
            ({'placeholder': 'Updated'}, {}),
            ({'placeholder': 'Updated'}, {'hint_text': 'Native hint'}),
            ({'placeholder': 'Restored'}, {}),
            ({'placeholder': ''}, {}), ({'placeholder': None}, {}), ({}, {}),
        ):
            self.root.options, self.root.native_options = options, overrides
            self.sync()
            self.assertIs(self.root.children[0].children[0].ui, native)
            self.assertEqual(native.password, field_type is MaskedField)
            self.assertEqual(native.hint_text, overrides.get('hint_text', options.get('placeholder')))
            self.assertEqual((native.value, model.value, edit.value), ('typed', '', 'typed'))
            self.assertEqual(events, [('input', 'typed')])
        native.on_submit(SimpleNamespace(control=native))
        self.assertEqual(model.value, 'typed')
        self.assertEqual(events, [('input', 'typed'), ('change', 'typed')])

    async def test_disabled_controls_and_native_override_removal(self):
        index, text = DummyBinding(1), DummyBinding('two')
        changes = []

        flag, choice = DummyBinding(True), DummyBinding("one")

        class Example(Application):
            options = {'disabled': True}
            native_options = {}
            def content(self):
                with Window():
                    with VBox():
                        Button('Run', **self.options).flet(**self.native_options)
                        for editable in (False, True):
                            with ComboBox(editable, index, text, **self.options).id(editable).flet(**self.native_options).change(lambda e: changes.append(e.value)):
                                ComboBoxItem('First', 'one')
                                ComboBoxItem('Second', 'two')
                        Checkbox("Check", flag, **self.options).flet(**self.native_options)
                        RadioButton("Radio", "two", choice, **self.options).flet(**self.native_options)

        await self.mount(Example())
        native = [node.ui for node in self.root.children[0].children[0].children]
        for options, overrides in (
            ({'disabled': True}, {}), ({'disabled': False}, {}),
            ({'disabled': True}, {'disabled': False}), ({'disabled': True}, {}),
            ({'disabled': False}, {'disabled': True}), ({}, {}),
        ):
            self.root.options, self.root.native_options = options, overrides
            self.sync()
            controls = self.root.children[0].children[0].children
            expected = overrides.get('disabled', options.get('disabled', False))
            for node, ui in zip(controls, native):
                self.assertIs(node.ui, ui)
                self.assertEqual(ui.disabled, expected)
            for combo in controls[1:3]:
                self.assertEqual((combo.ui.value, combo.ui.text), ('1', 'Second'))
                self.assertEqual(combo.ui.editable, combo.editable)
            self.assertEqual((index.value, text.value), (1, 'two'))
            check, radio = controls[3:]
            self.assertTrue(check.ui.value)
            self.assertEqual(radio.ui.value, 'one')
            flag.value, choice.value = True, 'one'
            self.assertEqual(changes, [])

    async def test_native_controls_reorder_style_and_bindings(self):
        model = DummyBinding([])
        clicks = []
        class Example(Application):
            order = ['a', 'b']
            styled = True
            def content(self):
                with Window():
                    with VBox():
                        for item in self.order:
                            Button(item).id(item)
                        Checkbox('check', model, 'yes').click(lambda e: clicks.append(e))
                        label = Label('styled').layout(padding=(1, 2, 3, 4), weight=1)
                        if self.styled:
                            label.style(color=0, bgColor=0, fontSize=18)
        await self.mount(Example())
        box = self.root.children[0].children[0]
        controls = {n._id: n.ui for n in box.children[:2]}
        self.assertIsInstance(controls['a'], ft.Button)
        checkbox, label = box.children[-2:]
        self.assertFalse(checkbox.ui.value)
        checkbox.ui.value = True
        checkbox._changed(SimpleNamespace(control=checkbox.ui))
        self.assertEqual(model.value, ['yes'])
        self.assertEqual(len(clicks), 1)
        self.assertEqual(label.ui.style.color, '#000000')
        self.assertEqual(label.outer.padding.left, 4)
        self.root.order = ['b', 'a']
        self.root.styled = False
        self.sync()
        box = self.root.children[0].children[0]
        self.assertIs(box.children[0].ui, controls['b'])
        self.assertIsNone(box.children[-1].ui.style.color)

    async def test_editor_rebinds_and_commits_once(self):
        model, edit = DummyBinding('initial'), DummyBinding('')
        events = []
        class Example(Application):
            def content(self):
                with Window():
                    TextField(model, edit).input(lambda e: events.append(('input', e.value))).change(lambda e: events.append(('change', e.value)))
        await self.mount(Example())
        field = self.root.children[0].children[0]
        field.ui.value = 'typed'
        field.ui.on_change(SimpleNamespace(control=field.ui))
        self.sync()
        field = self.root.children[0].children[0]
        event = SimpleNamespace(control=field.ui)
        field.ui.on_submit(event)
        field.ui.on_blur(event)
        self.assertEqual(events, [('input', 'typed'), ('change', 'typed')])
        self.assertEqual(model.value, 'typed')

    async def test_textfield_expands_only_along_a_row(self):
        class Example(Application):
            def content(self):
                with Window():
                    with VBox():
                        with HBox():
                            TextField(DummyBinding('row'))
                        TextField(DummyBinding('column'))

        await self.mount(Example())
        column = self.root.children[0].children[0]
        row_field = column.children[0].children[0]
        column_field = column.children[1]
        self.assertIs(row_field.outer.expand, True)
        self.assertIsNone(column_field.outer.expand)
        self.assertIsNone(row_field.outer.height)
        self.assertIsNone(column_field.outer.height)
        self.assertIsNone(row_field.ui.expand)
        self.assertIsNone(column_field.ui.expand)

    async def test_initial_window_flags_and_tabs(self):
        class Example(Application):
            flags = True
            order = ['a', 'b']
            def content(self):
                with Window(maximize=self.flags, fullscreen=self.flags):
                    with Tabs():
                        for item in self.order:
                            with Tab(item).id(item):
                                Label(item)
        await self.mount(Example())
        tabs = self.root.children[0].children[0]
        selected = tabs.pages[1].ui
        await self.session.dispatch_event(tabs.ui._i, 'change', 1)
        await asyncio.sleep(0)
        self.root.flags = False
        self.root.order = ['b', 'a']
        self.sync()
        window = self.root.children[0]
        self.assertTrue(window.ui.window.maximized)
        self.assertTrue(window.ui.window.full_screen)
        window.maximize(False).fullscreen(False)
        self.assertFalse(window.ui.window.maximized)
        tabs = window.children[0]
        self.assertIs(tabs.pages[0].ui, selected)
        self.assertEqual(tabs.ui.selected_index, 0)
        self.assertEqual(tabs.ui.length, 2)
        self.assertEqual(tabs.bar.tabs[0].label, 'b')

    async def test_redraw_burst_is_coalesced_on_loop(self):
        class Example(Application):
            builds = 0
            def content(self):
                self.builds += 1
                with Window():
                    Label(str(self.builds))
        await self.mount(Example())
        for _ in range(1000):
            self.root.redraw()
        await asyncio.sleep(0)
        self.assertEqual(self.root.builds, 2)

    async def test_dropdown_empty_invalid_and_distinct_item_values(self):
        index, text = DummyBinding(-1), DummyBinding('')
        class Example(Application):
            items = [('first', 'one'), ('second', 'two')]
            def content(self):
                with Window():
                    with ComboBox(editable=True, index_model=index, text_model=text):
                        for label, value in self.items:
                            ComboBoxItem(label, value)
        await self.mount(Example())
        combo = self.root.children[0].children[0]
        self.assertIsNone(combo.ui.value)
        combo.ui.value, combo.ui.text = '1', 'second'
        combo.on_select(SimpleNamespace(control=combo.ui))
        combo.on_text_change(SimpleNamespace(control=combo.ui))
        self.assertEqual(index.value, 1)
        self.assertEqual(text.value, 'two')
        combo.ui.value, combo.ui.text = None, 'typed'
        combo.on_text_change(SimpleNamespace(control=combo.ui))
        self.assertEqual(text.value, 'typed')
        self.sync()
        self.assertEqual(self.root.children[0].children[0].ui.text, 'typed')
        self.assertEqual(index.value, -1)
        self.root.items = []
        self.sync()
        self.assertIsNone(self.root.children[0].children[0].ui.value)

    async def test_canvas_shapes_image_and_progress(self):
        def painter(canvas):
            canvas.drawText(0, 0, 'text', size=18, color=0, rotate=90)
            canvas.drawRect(30, 30, 10, 10, fill=0xFF0000)
            canvas.drawEllipse(50, 50, 5, 10, stroke=0)
            canvas.drawCubicBezier((0, 0), (10, 10), (20, 10), (30, 0), color=0)
        image = Path(__file__).resolve().parents[1] / 'screenshots' / 'hello_world.png'
        class Example(Application):
            def content(self):
                with Window():
                    with VBox():
                        Canvas(painter).layout(width=100, height=100)
                        Image(image).layout(width=80, height=40)
                        ProgressBar(2)
        await self.mount(Example())
        canvas, image, progress = self.root.children[0].children[0].children
        self.assertIsInstance(canvas.ui.shapes[0], cv.Text)
        rectangle = canvas.ui.shapes[1]
        self.assertEqual((rectangle.x, rectangle.y, rectangle.width, rectangle.height), (10, 10, 20, 20))
        self.assertIsInstance(canvas.ui.shapes[-1].elements[-1], cv.Path.CubicTo)
        self.assertTrue(image.ui.src.startswith(b'\x89PNG'))
        self.assertEqual(progress.ui.value, 1)

    async def test_end_scroll_request_uses_native_auto_scroll(self):
        class Example(Application):
            def content(self):
                with Window():
                    with Scroll().scrollY(Scroll.END):
                        Label('content')
        await self.mount(Example())
        scroll = self.root.children[0].children[0]
        self.assertTrue(scroll.ui.auto_scroll)
        self.assertEqual(scroll.scroll_state['requests'][1], (-1.0, 0))
        # The recording transport has no Flutter responder; stop the method task.
        scroll.scroll_state['task'].cancel()

    async def test_weighted_canvas_waits_for_size_and_ignores_duplicate_resize(self):
        paints = []
        class Example(Application):
            colour = 0xFF0000
            visible = True
            def content(self):
                with Window():
                    with HBox():
                        with VBox().layout(weight=1):
                            if self.visible:
                                Canvas(self.painter, self.colour).layout(weight=1)
                        Label('sidebar').layout(width=200)

            @staticmethod
            def painter(canvas, colour):
                paints.append((canvas.width, canvas.height, colour))
                canvas.drawRect(0, 0, canvas.width, canvas.height, fill=colour)

        await self.mount(Example())
        canvas = self.root.children[0].children[0].children[0].children[0]
        native = canvas.ui
        self.assertTrue(native.expand)
        self.assertEqual(paints, [])  # Initial-fit painters must not see 0 x 0.
        with self.assertNoLogs('flet', level='ERROR'):
            for width, height in [(0, 300), (400, 0), (float('inf'), 300)]:
                await self.session.dispatch_event(native._i, 'resize', {'w': width, 'h': height})
            self.assertEqual(paints, [])
            await self.session.dispatch_event(native._i, 'resize', {'w': 400, 'h': 300})
            self.assertEqual(paints, [(400, 300, 0xFF0000)])
            self.assertEqual((native.shapes[0].width, native.shapes[0].height), (400, 300))
            updates = len(self.connection.messages)
            await self.session.dispatch_event(native._i, 'resize', {'w': 400, 'h': 300})
            self.assertEqual(len(paints), 1)
            self.assertEqual(len(self.connection.messages), updates)

        self.root.colour = 0x0000FF
        self.sync()
        current = self.root.children[0].children[0].children[0].children[0]
        self.assertIs(current.ui, native)
        self.assertEqual(paints[-1], (400, 300, 0x0000FF))
        # A queued callback from the retired declaration must use the new painter.
        canvas.on_resize(SimpleNamespace(width=500, height=350))
        self.assertEqual(paints[-1], (500, 350, 0x0000FF))
        self.assertEqual(len(paints), 3)

        self.root.visible = False
        self.sync()
        canvas.on_resize(SimpleNamespace(width=600, height=400))
        self.assertEqual(len(paints), 3)

    async def test_canvas_switches_between_fixed_and_weighted_sizes(self):
        paints = []
        class Example(Application):
            fixed = False
            def content(self):
                with Window():
                    canvas = Canvas(lambda node: paints.append((node.width, node.height)))
                    if self.fixed:
                        canvas.layout(width=120, height=80, weight=0)
                    else:
                        canvas.layout(weight=1)
        await self.mount(Example())
        native = self.root.children[0].children[0].ui
        await self.session.dispatch_event(native._i, 'resize', {'w': 400, 'h': 300})
        self.root.fixed = True
        self.sync()
        self.assertFalse(native.expand)
        self.assertEqual((native.width, native.height), (120, 80))
        self.assertEqual(paints[-1], (120, 80))
        self.root.fixed = False
        self.sync()
        self.assertTrue(native.expand)
        await self.session.dispatch_event(native._i, 'resize', {'w': 500, 'h': 400})
        self.assertEqual(paints[-1], (500, 400))

    async def test_focus_commit_before_label_click_and_worker_window_state(self):
        model = DummyBinding('initial')
        seen = []
        class Example(Application):
            def content(self):
                with Window(maximize=True):
                    with VBox():
                        TextField(model)
                        Label('click').click(lambda e: seen.append(model.value))
        await self.mount(Example())
        window = self.root.children[0]
        field, label = window.children[0].children
        field.ui.value = 'edited'
        field.on_focus(SimpleNamespace(control=field.ui))
        field.on_textbox_changed(SimpleNamespace(control=field.ui))
        self.assertIsNotNone(label.outer.on_click)
        await self.session.dispatch_event(label.outer._i, 'click', None)
        self.assertEqual(seen, ['edited'])
        await asyncio.to_thread(window.maximize, False)
        await asyncio.sleep(0)
        self.assertFalse(window.ui.window.maximized)

    async def test_label_native_click_routing_rebinds_and_clears(self):
        seen = []
        class Example(Application):
            selectable = False
            enabled = True
            value = 'first'
            def content(self):
                with Window():
                    label = Label('click', selectable=self.selectable)
                    if self.enabled:
                        label.click(lambda e, value: seen.append(value), self.value)
        await self.mount(Example())
        label = self.root.children[0].children[0]
        text, shell = label.ui, label.outer
        self.assertFalse(text.selectable)
        self.assertIsNotNone(shell.on_click)
        await self.session.dispatch_event(shell._i, 'click', None)
        self.assertEqual(seen, ['first'])

        self.root.value = 'rebound'
        self.sync()
        label = self.root.children[0].children[0]
        self.assertIs(label.ui, text)
        self.assertIs(label.outer, shell)
        await self.session.dispatch_event(shell._i, 'click', None)
        self.assertEqual(seen, ['first', 'rebound'])

        self.root.selectable = True
        self.sync()
        self.assertTrue(text.selectable)
        self.assertIsNone(shell.on_click)
        self.assertIsNotNone(text.on_tap)
        await self.session.dispatch_event(text._i, 'tap', None)
        self.assertEqual(seen, ['first', 'rebound', 'rebound'])

        self.root.enabled = False
        self.sync()
        self.assertIsNone(text.on_tap)
        self.assertIsNone(shell.on_click)
        self.root.selectable = False
        self.sync()
        self.assertIsNone(text.on_tap)
        self.assertIsNone(shell.on_click)
