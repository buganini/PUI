"""env/bin/python -m unittest discover -s tests -p flet_regression.py"""
import asyncio
import contextlib
import io
import unittest
from types import SimpleNamespace

import flet as ft
from flet.messaging.connection import Connection
from flet.messaging.session import Session
from flet.pubsub.pubsub_hub import PubSubHub
from PUI.flet import Application, Window, VBox, Label, Button, Checkbox, TextField, DummyBinding, Tabs, Tab, Scroll
from PUI.dom import recur_delete


class RecordingConnection(Connection):
    """Real Flet Session with a recording transport; no Flutter client simulated."""
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.pubsubhub = PubSubHub(loop=loop)
        self.messages = []

    def send_message(self, message):
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
        tabs.ui.selected_index = 1
        selected = tabs.pages[1].ui
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
