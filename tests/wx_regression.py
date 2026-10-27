"""Run with python3 -m unittest discover -s tests -p wx_regression.py (GUI required)."""
import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

import wx
from PUI.wx import Application, PUI, PUIView, Window, VBox, HBox, Grid, Spacer, Label, Button, Checkbox, RadioButton, TextField, MaskedField, ComboBox, ComboBoxItem, ProgressBar, DummyBinding, Scroll, Tabs, Tab, Text, Image, Canvas, ImageResource, MenuBar, Menu, MenuAction, Html
from PUI.dom import recur_delete


class WxRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.GetApp() or wx.App()

    def tearDown(self):
        for view in list(PUIView.__ALLVIEWS__):
            if isinstance(view, PUIView) and not view.destroyed:
                recur_delete(view, view, True)
        for window in wx.GetTopLevelWindows():
            window.Destroy()
        self.pump()

    def pump(self):
        for _ in range(4):
            self.app.Yield()
            self.app.ProcessPendingEvents()

    def sync(self, root):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            root.sync()
        self.assertNotIn('<ERROR', output.getvalue())

    def test_literal_ampersands_in_labels_and_buttons(self):
        class Example(Application):
            text = 'State & Binding'

            def content(self):
                with Window(size=(600, 300)):
                    with VBox():
                        Label(self.text)
                        Label(self.text).style(bgColor=0x234567)
                        Label(self.text, selectable=True)
                        Button(self.text)
                        Button(self.text).style(bgColor=0x234567)

        root = Example()
        for text in ('State & Binding', 'A && B & C'):
            root.text = text
            self.sync(root)
            self.pump()
            for node in root.children[0].children[0].children:
                control = node.ui
                if isinstance(control, wx.TextCtrl):
                    actual = control.GetValue()
                elif isinstance(control, (wx.StaticText, wx.Button)):
                    actual = control.GetLabelText()
                else:
                    actual = control.GetLabel()
                self.assertEqual(actual, text)

    def test_button_content_sizing_native_and_coloured(self):
        class Example(Application):
            text = 'OK'
            width = None
            weight = None
            styled = False
            def content(self):
                with Window(size=(600, 300)):
                    with HBox().layout(padding=0):
                        node = Button(self.text).id('button').layout(width=self.width, weight=self.weight)
                        if self.styled:
                            node.style(bgColor=0x234567)
                        Spacer()
        root = Example()
        for styled in (False, True, False):
            root.styled = styled
            self.sync(root)
            self.pump()
            button = root.children[0].children[0].children[0].ui
            control_type = type(button)
            default = control_type(button.GetParent(), label='OK')
            fitted = control_type(button.GetParent(), label='OK', style=wx.BU_EXACTFIT)
            self.assertEqual(button.GetBestSize(), fitted.GetBestSize())
            self.assertLessEqual(button.GetBestSize().width, default.GetBestSize().width)
            initial = button.GetBestSize().width
            root.width = 180
            self.sync(root)
            self.pump()
            self.assertGreaterEqual(button.GetSize().width, 180)
            root.width, root.weight = None, 1
            self.sync(root)
            self.pump()
            self.assertGreater(button.GetSize().width, 200)
            root.weight, root.text = None, 'A much longer button caption'
            self.sync(root)
            self.pump()
            self.assertGreater(button.GetBestSize().width, initial)
            root.text = 'OK'
            self.sync(root)
            self.pump()
            self.assertIs(root.children[0].children[0].children[0].ui, button)
            self.assertEqual(button.GetBestSize().width, initial)
            default.Destroy()
            fitted.Destroy()

    def test_native_autocomplete_toggle_and_choice_updates(self):
        text = DummyBinding('free text')
        class Example(Application):
            completion = True
            labels = ['Taipei', 'Tokyo']
            def content(self):
                with Window():
                    with ComboBox(editable=True, text_model=text, autoexpand=self.completion):
                        for label in self.labels:
                            ComboBoxItem(label)
        root = self.root = Example()
        self.sync(root)
        combo = root.children[0].children[0].ui
        for enabled, labels in [(True, ['Taipei', 'Tokyo']), (False, ['Taipei']), (True, ['Seoul'])]:
            root.completion, root.labels = enabled, labels
            self.sync(root)
            node = root.children[0].children[0]
            self.assertIs(node.ui, combo)
            self.assertEqual(combo.GetValue(), 'free text')
            node.completion.refresh(show=True)
            self.assertEqual(node.completion.popup.IsShown(), enabled)

    def test_keyword_candidates_survive_sync_and_select_original_value(self):
        text = DummyBinding('tai tok')
        class Example(Application):
            def content(self):
                with Window(size=(500, 300)):
                    with ComboBox(editable=True, text_model=text):
                        ComboBoxItem('Amsterdam', 'AMS')
                        ComboBoxItem('Taipei', 'TPE')
                        ComboBoxItem('Tokyo', 'HND')
        root = self.root = Example()
        root.sync()
        node = root.children[0].children[0]
        self.pump()
        node.completion.refresh(show=True)
        self.assertEqual(node.completion.indices, [0, 1, 2])
        root.sync()
        node = root.children[0].children[0]
        self.assertIs(node.completion.node, node)
        node.completion.rows.SetSelection(2)
        node.completion.select()
        self.assertEqual(text.value, 'HND')
        self.assertEqual(node.ui.GetValue(), 'Tokyo')
        self.assertFalse(node.completion.popup.IsShown())

    def test_completion_stays_open_after_bound_text_relayout(self):
        from PUI.wx import State
        state = State()
        state.text = ''
        state.query = ''

        class Example(Application):
            def content(self):
                with Window(size=(500, 300)):
                    with VBox():
                        Label(state.text)
                        with ComboBox(editable=True, text_model=state('text'), edit_model=state('query')):
                            ComboBoxItem('Taipei', 'TPE')
                            ComboBoxItem('Tokyo', 'HND')

        root = self.root = Example()
        self.sync(root)
        self.pump()
        combo = root.children[0].children[0].children[1].ui
        combo.SetFocus()
        for text in ('t', 'tai', 'tai tok'):
            combo.SetValue(text)
            self.pump()
            node = root.children[0].children[0].children[1]
            self.assertEqual(state.text, text)
            self.assertEqual(state.query, text)
            self.assertIs(node.ui, combo)
            self.assertTrue(node.completion.popup.IsShown())
            event = wx.SizeEvent(combo.GetSize(), combo.GetId())
            event.SetEventObject(combo)
            combo.GetEventHandler().ProcessEvent(event)
            self.pump()
            self.assertTrue(node.completion.popup.IsShown())
        from unittest.mock import Mock
        event = Mock()
        event.GetKeyCode.return_value = wx.WXK_ESCAPE
        node.completion.key(event)
        self.pump()
        self.assertFalse(node.completion.popup.IsShown())
        self.assertEqual(combo.GetValue(), 'tai tok')

    def test_completion_tracks_resize_and_ancestor_movement(self):
        from types import SimpleNamespace
        from PUI.wx.completion import Completion
        frame = wx.Frame(None, size=(600, 400), pos=(40, 40))
        host = wx.Panel(frame)
        panel = wx.Panel(host, size=(300, 200))
        combo = wx.ComboBox(panel, pos=(10, 10), size=(180, 30))
        node = SimpleNamespace(
            ui=combo, destroyed=False, editable=True, autoexpand=True, disabled=False,
            children=[SimpleNamespace(text='Taipei', key='taipei')])
        completion = Completion(node)

        def settle():
            wx.CallLater(100, self.app.ExitMainLoop)
            self.app.MainLoop()

        try:
            frame.Show()
            combo.SetFocus()
            settle()
            combo.ChangeValue('tai')
            completion.refresh(show=True)
            self.pump()
            frame.SetSize((900, 450))
            # Sizers move descendants after native size handlers. Model that
            # ordering explicitly instead of depending on the window manager.
            completion.geometry_event(wx.SizeEvent(frame.GetSize()))
            panel.Move((300, 20))
            settle()
            self.assertTrue(completion.popup.IsShown())
            self.assertEqual(completion.popup.GetPosition(),
                             combo.ClientToScreen((0, combo.GetSize().height)))
            panel.Move((70, 60))
            settle()
            self.assertEqual(completion.popup.GetPosition(),
                             combo.ClientToScreen((0, combo.GetSize().height)))
            combo.SetSize((220, 30))
            settle()
            self.assertEqual(completion.popup.GetSize().width, 220)
            # A queued geometry update must not reopen an Escape-dismissed menu.
            completion.geometry_event(wx.SizeEvent(frame.GetSize()))
            completion.hide()
            self.pump()
            self.assertFalse(completion.popup.IsShown())
            completion.popup.Show()
            completion.geometry_event(wx.SizeEvent(frame.GetSize()))
        finally:
            completion.destroy()
            self.pump()  # Queued callback must tolerate destruction.
            frame.Destroy()

    def test_adaptive_box_retains_editor(self):
        from PUI.wx import HVBox
        class Example(Application):
            def content(self):
                with Window(size=(800,400)):
                    with VBox().layout(weight=1):
                        with HVBox(600):
                            TextField(DummyBinding('retained'))
                            Label('second')
        root = self.root = Example()
        root.sync()
        for _ in range(12): self.pump()
        editor = root.children[0].children[0].children[0].children[0].ui
        for width in (500,800,500,800):
            root.children[0].ui.SetClientSize((width,400))
            for _ in range(12): self.pump()
            box = root.children[0].children[0].children[0]
            self.assertIs(box.children[0].ui, editor)
            self.assertEqual(box.container_x, width>=600)
            self.assertEqual(box.ui.GetOrientation(), wx.HORIZONTAL if width>=600 else wx.VERTICAL)

    def test_adaptive_size_and_breakpoints(self):
        class Example(Application):
            def content(self):
                with Window(size=(800, 400)):
                    with VBox().layout(weight=1).id('adaptive') as container:
                        self.binding = container.size()
                        with VBox().visible(False).wideVisible(600, True):
                            Label('wide')
                        with VBox().wideVisible(600, False):
                            Label('compact')
        root = Example()
        root.sync()
        for _ in range(12): self.pump()
        original = root.children[0].children[0]._state
        self.assertIsNotNone(root.binding.value)
        for width in (500, 800, 500, 800):
            root.children[0].ui.SetClientSize((width, 400))
            for _ in range(12): self.pump()

            container = root.children[0].children[0]
            self.assertIs(container._state, original)
            self.assertEqual(container.children[0]._visible, width >= 600)
            self.assertEqual(container.children[1]._visible, width < 600)
            self.assertEqual(root.binding.value, container._state.size)

    def test_visibility_retains_widget_and_collapses_layout(self):
        class Example(Application):
            shown = True
            def content(self):
                with Window(size=(400, 300)):
                    with VBox():
                        Label('Before')
                        with VBox().visible(self.shown).layout(padding=12):
                            TextField(DummyBinding('retained'))
                            Label('Always hidden').visible(False)
                        Label('After')
        root = Example()
        native = None
        for shown in (True, False, True, False, True):
            root.shown = shown
            root.sync()
            self.pump()
            box = root.children[0].children[0].children[1]
            if native is None:
                native = box.ui
            self.assertIs(box.ui, native)
            self.assertEqual(box.children[0].ui.IsShown(), shown)
            self.assertFalse(box.children[1].ui.IsShown())
            parent = root.children[0].children[0]
            self.assertEqual(parent.sizerItems[1][1].IsShown(), shown)

    def test_window_default_background_is_not_written_as_transparent(self):
        class Example(Application):
            background = None
            def content(self):
                with Window().style(bgColor=self.background):
                    Label('content')
        root = Example()
        with patch.object(wx.Frame, 'SetBackgroundColour', autospec=True) as setter:
            self.sync(root)
            self.sync(root)
            setter.assert_not_called()
            root.background = 0x123456
            self.sync(root)
            self.assertEqual(setter.call_args.args[-1], wx.Colour(0x12, 0x34, 0x56))
            root.background = None
            self.sync(root)
            self.assertFalse(setter.call_args.args[-1].IsOk())
            count = setter.call_count
            self.sync(root)
            self.assertEqual(setter.call_count, count)

    def test_tabs_expand_across_vbox_width(self):
        class Example(Application):
            def content(self):
                with Window(size=(600, 400)):
                    with VBox():
                        with Tabs():
                            with Tab('Page'):
                                Label('short')
        root = Example()
        self.sync(root)
        self.pump()
        window = root.children[0]
        tabs = window.children[0].children[0]
        self.assertGreater(tabs.ui.GetSize().width, 500)
        window.ui.SetSize((800, 400))
        self.pump()
        self.assertGreater(tabs.ui.GetSize().width, 700)

    def test_placeholder_updates_preserve_edit_buffer_and_signals(self):
        self.check_textfield(TextField)

    def test_maskedfield_preserves_binding_and_edit_buffer(self):
        self.check_textfield(MaskedField)

    def check_textfield(self, field_type):
        model, edit = DummyBinding(''), DummyBinding('')
        events = []

        class Example(Application):
            options = {'placeholder': 'Enter text'}
            def content(self):
                with Window():
                    field_type(model, edit, **self.options).input(lambda e: events.append(('input', e.value))).change(lambda e: events.append(('change', e.value)))

        root = Example()
        self.sync(root)
        self.pump()
        native = root.children[0].children[0].ui
        self.assertEqual(bool(native.GetWindowStyleFlag() & wx.TE_PASSWORD), field_type is MaskedField)
        self.assertEqual(native.GetHint(), 'Enter text')
        self.assertEqual((native.GetValue(), model.value, edit.value), ('', '', ''))
        self.assertEqual(events, [])
        native.SetValue('typed')
        self.pump()
        native.SetInsertionPoint(2)
        for options in ({'placeholder': 'Updated'}, {'placeholder': ''}, {'placeholder': None}, {}):
            root.options = options
            self.sync(root)
            self.pump()
            self.assertIs(root.children[0].children[0].ui, native)
            self.assertEqual(bool(native.GetWindowStyleFlag() & wx.TE_PASSWORD), field_type is MaskedField)
            self.assertEqual(native.GetHint(), options.get('placeholder') or '')
            self.assertEqual((native.GetValue(), model.value, edit.value), ('typed', '', 'typed'))
            self.assertEqual(native.GetInsertionPoint(), 2)
            self.assertEqual(events, [('input', 'typed')])
        root.children[0].children[0].commit()
        self.assertEqual(model.value, 'typed')
        self.assertEqual(events, [('input', 'typed'), ('change', 'typed')])

    def test_redraw_coalesces_and_destroyed_queue_is_safe(self):
        view = PUIView()
        queued = []
        with patch('wx.CallAfter', side_effect=lambda cb: queued.append(cb)):
            for _ in range(1000):
                view.redraw()
        self.assertEqual(len(queued), 1)
        self.assertTrue(view.updating)
        recur_delete(view, view, True)
        queued.pop()()
        self.assertFalse(view.updating)

    def test_application_title_and_explicit_window_titles(self):
        class Example(Application):
            window_title = None
            def content(self):
                with Window(title=self.window_title):
                    Label('Title')
        original = self.app.GetAppDisplayName()
        root = Example(title='Application title')
        try:
            native = None
            for title in (None, 'Document', '', None):
                root.window_title = title
                self.sync(root)
                window = root.children[0].ui
                if native is not None:
                    self.assertIs(window, native)
                native = window
                self.assertEqual(window.GetTitle(), 'Application title' if title is None else title)
                self.assertEqual(self.app.GetAppDisplayName(), 'Application title')
        finally:
            self.app.SetAppDisplayName(original)

    def test_disabled_controls_retain_widgets_and_models(self):
        index, text = DummyBinding(1), DummyBinding('two')
        changes = []

        flag, choice = DummyBinding(True), DummyBinding("one")

        class Example(Application):
            options = {'disabled': True}
            def content(self):
                with Window():
                    with VBox():
                        Button('Run', **self.options)
                        for editable in (False, True):
                            with ComboBox(editable, index_model=index, text_model=text, **self.options).id(editable).change(lambda e: changes.append(e.value)):
                                ComboBoxItem('First', 'one')
                                ComboBoxItem('Second', 'two')
                        Checkbox("Check", flag, **self.options)
                        RadioButton("Radio", "two", choice, **self.options)

        root = Example()
        root.ui = self.app
        native = None
        for options in ({'disabled': True}, {'disabled': False}, {'disabled': True}, {}):
            root.options = options
            self.sync(root)
            self.pump()
            controls = root.children[0].children[0].children
            if native is None:
                native = [node.ui for node in controls]
            for node, ui in zip(controls, native):
                self.assertIs(node.ui, ui)
                self.assertEqual(ui.IsEnabled(), not options.get('disabled', False))
            for combo in controls[1:3]:
                self.assertEqual(combo.ui.GetSelection(), 1)
                self.assertEqual(combo.ui.GetValue(), 'Second')
                self.assertEqual(combo.ui.IsEditable(), combo.editable)
            self.assertEqual((index.value, text.value), (1, 'two'))
            check, radio = controls[3:]
            self.assertTrue(check.ui.GetValue())
            self.assertFalse(radio.ui.GetValue())
            flag.value, choice.value = True, 'one'
            self.assertEqual(changes, [])

    def test_decorator_uses_wx_view(self):
        @PUI
        def Child():
            Label('child')
        self.assertIsInstance(Child(), PUIView)

    def test_keyed_reorder_reuses_widgets_and_updates_callbacks(self):
        calls = []
        class Example(Application):
            order = ['a', 'b', 'c']
            generation = 0
            def content(self):
                with Window(size=(320, 240)):
                    with VBox():
                        for key in self.order:
                            Button(key).id(key).click(lambda e, value: calls.append(value), self.generation)
        root = Example()
        self.sync(root)
        box = root.children[0].children[0]
        widgets = {n._id: n.ui for n in box.children}
        self.assertIs(widgets['a'].GetParent(), root.children[0].panel)
        root.order = ['c', 'a']
        root.generation = 1
        self.sync(root)
        box = root.children[0].children[0]
        self.assertEqual([n._id for n in box.children], ['c', 'a'])
        for node in box.children:
            self.assertIs(node.ui, widgets[node._id])
            node._clicked()
        self.assertEqual(calls, [1, 1])
        self.pump()
        self.assertFalse(bool(widgets['b']))

    def test_replace_window_content_and_remove_layout_subtree(self):
        class Example(Application):
            show_layout = True
            def content(self):
                with Window(size=(320, 240)):
                    if self.show_layout:
                        with VBox():
                            Label('inside')
                    else:
                        Label('direct')
        root = Example()
        self.sync(root)
        old = root.children[0].children[0].children[0].ui
        root.show_layout = False
        self.sync(root)
        self.pump()
        window = root.children[0]
        self.assertFalse(bool(old))
        self.assertIs(window.children[0].ui.GetParent(), window.panel)
        self.assertIs(window.content_mount[2].GetWindow(), window.children[0].ui)

    @unittest.skipUnless(wx.Platform == '__WXMSW__', 'MSW overlapping text painting')
    def test_stack_text_pixels_follow_declaration_order(self):
        from PUI.wx import Stack

        class Example(Application):
            order = ['bottom', 'top']
            top_visible = True

            def content(self):
                with Window(size=(400, 300)):
                    with Stack():
                        for name in self.order:
                            Label('MMMM').id(name).style(
                                fontSize=48,
                                color=0x244B5A if name == 'bottom' else 0xA84A3A,
                            ).visible(name != 'top' or self.top_visible)

        root = Example()
        self.sync(root)
        self.pump()

        def assert_pixels(expected, covered):
            stack = root.children[0].children[0]
            # Exercise the same compositor used by EVT_PAINT on every visible
            # sibling: any one of these may be the last MSW window to repaint.
            for child in stack.children:
                control = child.ui
                if not control.IsShown():
                    continue
                bitmap = wx.Bitmap(*control.GetClientSize())
                dc = wx.MemoryDC(bitmap)
                control.paint_layers(dc)
                dc.SelectObject(wx.NullBitmap)
                pixels = bytes(bitmap.ConvertToImage().GetData())
                colours = set(zip(pixels[0::3], pixels[1::3], pixels[2::3]))
                self.assertIn(expected, colours)
                self.assertNotIn(covered, colours)

        red, blue = (0xA8, 0x4A, 0x3A), (0x24, 0x4B, 0x5A)
        assert_pixels(red, blue)
        root.order = ['top', 'bottom']
        self.sync(root)
        self.pump()
        assert_pixels(blue, red)
        root.order = ['bottom', 'top']
        root.top_visible = False
        self.sync(root)
        self.pump()
        assert_pixels(blue, red)
        root.top_visible = True
        root.children[0].ui.SetClientSize((600, 400))
        self.sync(root)
        self.pump()
        assert_pixels(red, blue)

    @unittest.skipUnless(wx.Platform == '__WXMSW__', 'MSW overlapping text painting')
    def test_stack_labels_use_generic_painting_and_retain_updates(self):
        from PUI.wx import Stack
        from wx.lib.stattext import GenStaticText

        class Example(Application):
            order = ['Bottom', 'Top']
            suffix = ''

            def content(self):
                with Window(size=(400, 300)):
                    with VBox():
                        Label('Outside')
                        with Stack():
                            for name in self.order:
                                with VBox().id(name).layout(padding=0):
                                    Label(name + self.suffix).style(
                                        fontSize=48 if name == 'Bottom' else 32)

        root = Example()
        self.sync(root)
        self.pump()
        box = root.children[0].children[0]
        self.assertIsInstance(box.children[0].ui, wx.StaticText)
        stack = box.children[1]
        controls = {c._id: c.children[0].ui for c in stack.children}
        for control in controls.values():
            self.assertIsInstance(control, GenStaticText)
            self.assertTrue(control.GetWindowStyleFlag() & wx.CLIP_SIBLINGS)
            self.assertEqual(control.GetBackgroundStyle(), wx.BG_STYLE_TRANSPARENT)
        self.assertEqual(controls['Bottom'].GetPosition(), controls['Top'].GetPosition())

        root.order = ['Top', 'Bottom']
        root.suffix = ' updated'
        self.sync(root)
        self.pump()
        stack = root.children[0].children[0].children[1]
        for child in stack.children:
            self.assertIs(child.children[0].ui, controls[child._id])
            self.assertEqual(child.children[0].ui.GetLabel(), child._id + ' updated')
        root.children[0].ui.SetClientSize((600, 400))
        self.pump()
        self.assertEqual(controls['Bottom'].GetPosition(), controls['Top'].GetPosition())

    def test_stack_overlap_reorder_resize_and_remove(self):
        from PUI.wx import Stack
        class Example(Application):
            order = ['a', 'b']
            def content(self):
                with Window(size=(400, 300)):
                    with Stack().layout(padding=0):
                        for name in self.order:
                            with VBox().id(name).layout(padding=0):
                                Button(name).layout(padding=0)
        root = Example()
        self.sync(root)
        self.pump()
        stack = root.children[0].children[0]
        panel = stack.ui
        controls = {c._id: c.children[0].ui for c in stack.children}
        self.assertEqual(controls['a'].GetRect(), controls['b'].GetRect())
        self.assertEqual(controls['a'].GetParent(), panel)
        root.order = ['b', 'a']
        self.sync(root)
        self.pump()
        stack = root.children[0].children[0]
        self.assertIs(stack.ui, panel)
        self.assertIs(stack.children[0].children[0].ui, controls['b'])
        root.children[0].ui.SetClientSize((600, 400))
        self.pump()
        self.assertEqual(controls['a'].GetRect(), controls['b'].GetRect())
        self.assertGreater(panel.GetSize().width, 400)
        root.order = ['a']
        self.sync(root)
        self.pump()
        self.assertFalse(bool(controls['b']))
        root.order = []
        self.sync(root)
        self.pump()
        self.assertEqual(panel.GetSizer().GetItemCount(), 0)

    def test_layout_weights_padding_and_style_reset(self):
        class Example(Application):
            weight = 2
            styled = True
            def content(self):
                with Window(size=(400, 240)):
                    with HBox():
                        node = Label('first').layout(weight=self.weight, padding=(1, 2, 3, 4), width=60)
                        if self.styled:
                            node.style(color=0, bgColor=0, fontSize=18)
                        Label('second').layout(weight=1)
        root = Example()
        self.sync(root)
        box = root.children[0].children[0]
        first = box.children[0]
        self.assertEqual(first.ui.GetForegroundColour(), wx.Colour(0, 0, 0))
        self.assertEqual(first.ui.GetBackgroundColour(), wx.Colour(0, 0, 0))
        si = box.sizerItems[0][1]
        self.assertEqual(si.GetProportion(), 2)
        self.assertEqual([tuple(i.GetMinSize()) for i in si.padding_items], [(0, 1), (2, 0), (0, 3), (4, 0)])
        original = first.native_style
        root.weight = 0
        root.styled = False
        self.sync(root)
        box = root.children[0].children[0]
        self.assertEqual(box.sizerItems[0][1].GetProportion(), 0)
        self.assertEqual(box.children[0].ui.GetForegroundColour(), original[1])
        self.assertEqual(box.children[0].ui.GetFont().GetPointSize(), original[0].GetPointSize())
        root.weight = None
        self.sync(root)
        self.assertEqual(root.children[0].children[0].sizerItems[0][1].GetProportion(), 0)

    def test_coloured_controls_update_and_restore_native_button(self):
        class Example(Application):
            colour = 0x244B5A
            styled = True
            clicks = 0

            def clicked(self, event):
                self.clicks += 1

            def content(self):
                with Window(size=(400, 240)):
                    with VBox():
                        for cls in (Label, Text, Button):
                            node = cls('Styled')
                            if cls is Button:
                                node.click(self.clicked)
                            if self.styled:
                                node.style(color=0xFFF7E6, bgColor=self.colour)

        root = Example()
        self.sync(root)
        controls = [n.ui for n in root.children[0].children[0].children]
        if wx.Platform == '__WXMAC__':
            from wx.lib.stattext import GenStaticText
            from wx.lib.buttons import GenButton
            self.assertIsInstance(controls[0], GenStaticText)
            self.assertIsInstance(controls[1], GenStaticText)
            self.assertIsInstance(controls[2], GenButton)
        root.colour = 0xA84A3A
        self.sync(root)
        for node, control in zip(root.children[0].children[0].children, controls):
            self.assertIs(node.ui, control)
            self.assertEqual(control.GetBackgroundColour(), wx.Colour(168, 74, 58))
            self.assertEqual(control.GetForegroundColour(), wx.Colour(255, 247, 230))
        event = wx.CommandEvent(wx.EVT_BUTTON.typeId, controls[2].GetId())
        event.SetEventObject(controls[2])
        controls[2].GetEventHandler().ProcessEvent(event)
        self.assertEqual(root.clicks, 1)
        root.styled = False
        self.sync(root)
        restored = root.children[0].children[0].children
        self.assertIsInstance(restored[0].ui, wx.StaticText)
        self.assertIsInstance(restored[1].ui, wx.StaticText)
        self.assertIsInstance(restored[2].ui, wx.Button)

    @patch.object(Html, '_create_webview', side_effect=RuntimeError('forced fallback'))
    def test_html_fallback_style_reaches_parsed_text_and_preserves_inline_colour(self, _create):
        class Example(Application):
            colour = 0x1C2A30
            def content(self):
                with Window():
                    Html('MMMM <font color="#ff0000">MMMM</font>').style(
                        color=self.colour, bgColor=0xFFF7E6)
        root = Example()
        self.sync(root)
        # Small GTK glyphs can consist entirely of antialiased/subpixel pixels.
        # Larger glyphs have solid interiors for exact foreground-colour checks.
        root.children[0].children[0].ui.SetStandardFonts(24)
        for colour in (0x1C2A30, 0x0000FF):
            root.colour = colour
            self.sync(root)
            control = root.children[0].children[0].ui
            self.assertEqual(control.GetBackgroundColour(), wx.Colour(255, 247, 230))
            bitmap = wx.Bitmap(400, 100, 24)
            dc = wx.MemoryDC(bitmap)
            dc.SetBackground(wx.Brush(wx.WHITE))
            dc.Clear()
            cell = control.GetInternalRepresentation()
            cell.Layout(400)
            cell.Draw(dc, 0, 0, 0, 100, wx.html.HtmlRenderingInfo())
            dc.SelectObject(wx.NullBitmap)
            pixels = bytes(bitmap.ConvertToImage().GetData())
            colours = set(zip(pixels[0::3], pixels[1::3], pixels[2::3]))
            self.assertIn((colour >> 16, (colour >> 8) & 255, colour & 255), colours)
            self.assertIn((255, 0, 0), colours)

    @unittest.skipUnless(wx.Platform == '__WXMAC__', 'Cocoa label painting')
    def test_compact_label_paints_background_without_resize(self):
        class Example(Application):
            colour = 0x244B5A
            def content(self):
                with Window():
                    Label('MMMM').style(bgColor=self.colour, color=0xFFF7E6)
        root = Example()
        for colour in (0x244B5A, 0xA84A3A):
            root.colour = colour
            self.sync(root)
            control = root.children[0].children[0].ui
            bitmap = wx.Bitmap(120, 40)
            dc = wx.MemoryDC(bitmap)
            dc.SetBackground(wx.Brush(wx.Colour(255, 0, 255)))
            dc.Clear()
            with patch('PUI.wx.label.wx.PaintDC', return_value=dc):
                control.OnPaint(None)
            dc.SelectObject(wx.NullBitmap)
            image = bitmap.ConvertToImage()
            self.assertEqual((image.GetRed(119, 39), image.GetGreen(119, 39),
                              image.GetBlue(119, 39)),
                             (colour >> 16, (colour >> 8) & 255, colour & 255))

    def test_textfield_uses_native_size_and_expands_horizontally(self):
        model = DummyBinding('value')
        class Example(Application):
            def content(self):
                with Window(size=(400, 240)):
                    with VBox():
                        TextField(model)
                        Spacer()

        root = Example()
        self.sync(root)
        self.pump()
        box = root.children[0].children[0]
        field = box.children[0]
        self.assertIsNone(field.layout_width)
        self.assertIsNone(field.layout_height)
        self.assertEqual(tuple(field.ui.GetMinSize()), (-1, -1))
        self.assertTrue(box.sizerItems[0][1].GetFlag() & wx.EXPAND)
        self.assertGreater(field.ui.GetSize().width, field.ui.GetBestSize().width)
        self.assertEqual(field.ui.GetSize().height, field.ui.GetBestSize().height)

    def test_linear_layout_aligns_compact_children_and_retains_expansion(self):
        for box_type in (HBox, VBox):
            with self.subTest(box=box_type.__name__):
                class Example(Application):
                    def content(self):
                        with Window(size=(500, 320)):
                            with box_type().layout(padding=0):
                                Button('Short').layout(padding=0)
                                Label('A longer label').layout(padding=0)
                                TextField(DummyBinding('value')).layout(padding=0)

                root = Example()
                self.sync(root)
                self.pump()
                box = root.children[0].children[0]
                retained = [child.ui for child in box.children]
                for size in ((500, 320), (640, 420)):
                    self.sync(root)
                    self.pump()
                    box = root.children[0].children[0]
                    box.ui.SetDimension(0, 0, *size)
                    axis = 1 if box_type is HBox else 0
                    for i, (child, item) in enumerate(box.sizerItems):
                        self.assertIs(child.ui, retained[i])
                        if box_type is VBox and i == 2:
                            self.assertTrue(item.GetFlag() & wx.EXPAND)
                            self.assertEqual(child.ui.GetSize().width, size[0])
                        else:
                            if box_type is VBox:
                                self.assertEqual(child.ui.GetPosition().x, 0)
                            else:
                                actual = child.ui.GetPosition()[axis] + child.ui.GetSize()[axis] / 2
                                self.assertLessEqual(abs(actual - size[axis] / 2), 1)

    def test_grid_replacement_and_dimensions(self):
        class Example(Application):
            column = 0
            width = 120
            def content(self):
                with Window():
                    with Grid():
                        Label('cell').grid(row=0, column=self.column).layout(width=self.width)
        root = Example()
        self.sync(root)
        root.column = 1
        root.width = 40
        self.sync(root)
        grid = root.children[0].children[0]
        self.assertEqual(tuple(grid.sizerItems[0][1].GetPos()), (0, 1))
        self.assertEqual(grid.children[0].ui.GetMinSize().width, 40)

    def test_controls_programmatic_updates_and_commit(self):
        model, edit, index = DummyBinding('initial'), DummyBinding(''), DummyBinding(-1)
        events = []
        class Example(Application):
            items = ['one', 'two']
            def content(self):
                with Window():
                    with VBox():
                        TextField(model, edit).input(lambda e: events.append(('input', e.value))).change(lambda e: events.append(('change', e.value)))
                        with ComboBox(index_model=index):
                            for value in self.items:
                                ComboBoxItem(value)
                        ProgressBar(0.25)
        root = Example()
        self.sync(root)
        field, combo, gauge = root.children[0].children[0].children
        self.assertEqual(combo.ui.GetSelection(), -1)
        self.assertEqual(gauge.ui.GetValue(), 25)
        model.value = 'programmatic'
        self.sync(root)
        self.pump()
        field, combo, _ = root.children[0].children[0].children
        self.assertEqual(field.ui.GetValue(), 'programmatic')
        self.assertEqual(events, [])
        field.ui.ChangeValue('typed')
        field.on_textchanged(wx.CommandEvent(wx.EVT_TEXT.typeId))
        self.assertEqual(edit.value, 'typed')
        self.sync(root)
        field = root.children[0].children[0].children[0]
        field.commit()
        field.commit()
        self.assertEqual(model.value, 'typed')
        self.assertEqual(events, [('input', 'typed'), ('change', 'typed')])
        index.value = 100
        root.items = []
        self.sync(root)
        self.assertEqual(root.children[0].children[0].children[1].ui.GetCount(), 0)

    def test_dialog_filters_and_directory_alias(self):
        from PUI.wx.dialog import _directory, _wildcard
        self.assertEqual(_directory('/tmp', None), '/tmp')
        self.assertEqual(_directory(None, '/tmp'), '/tmp')
        with self.assertRaises(ValueError):
            _directory('/a', '/b')
        self.assertEqual(_wildcard('Images (*.png *.jpg);;All (*)'),
                         'Images (*.png *.jpg)|*.png;*.jpg|All (*)|*')
        self.assertEqual(_wildcard('Images|*.png'), 'Images|*.png')

    def test_scroll_offsets_growth_and_manual_position(self):
        class Example(Application):
            rows = 40
            target = Scroll.END
            def content(self):
                with Window(size=(280, 180)):
                    with Scroll(vertical=None).scrollY(self.target):
                        with VBox():
                            for i in range(self.rows):
                                Label(str(i)).id(str(i)).layout(height=24)
        root = Example()
        self.sync(root)
        self.pump()
        scroll = root.children[0].children[0]
        self.assertGreater(scroll.maximum(1), 0)
        self.assertEqual(scroll.ui.GetViewStart()[1], scroll.maximum(1))
        root.rows = 60
        self.sync(root)
        self.pump()
        scroll = root.children[0].children[0]
        self.assertEqual(scroll.ui.GetViewStart()[1], scroll.maximum(1))
        scroll.ui.Scroll(0, 80)
        self.sync(root)
        self.pump()
        scroll = root.children[0].children[0]
        self.assertEqual(scroll.ui.GetViewStart()[1], 80)
        root.target = 25
        self.sync(root)
        self.pump()
        self.assertEqual(root.children[0].children[0].ui.GetViewStart()[1], 25)
        root.target = -20
        self.sync(root)
        self.pump()
        scroll = root.children[0].children[0]
        self.assertEqual(scroll.ui.GetViewStart()[1], scroll.maximum(1) - 20)

    def test_tabs_reorder_labels_and_selectable_text(self):
        class Example(Application):
            order = ['a', 'b']
            suffix = ''
            def content(self):
                with Window():
                    with Tabs():
                        for key in self.order:
                            with Tab(key + self.suffix).id(key):
                                Text(key, selectable=True)
        root = Example()
        self.sync(root)
        tabs = root.children[0].children[0]
        pages = {page._id: page.ui for page in tabs.children}
        self.assertIsInstance(tabs.children[0].children[0].ui, wx.TextCtrl)
        root.order = ['b', 'a']
        root.suffix = '!'
        self.sync(root)
        tabs = root.children[0].children[0]
        self.assertEqual(tabs.ui.GetPageText(0), 'b!')
        self.assertIs(tabs.ui.GetPage(0), pages['b'])
        root.order = ['a']
        self.sync(root)
        self.assertEqual(root.children[0].children[0].ui.GetPageCount(), 1)

    def test_image_rescales_when_dimensions_change(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'image.png')
            image = wx.Image(20, 10)
            image.SetRGB(wx.Rect(0, 0, 20, 10), 255, 0, 0)
            image.SaveFile(path, wx.BITMAP_TYPE_PNG)
            class Example(Application):
                width = 40
                def content(self):
                    with Window():
                        Image(path).layout(width=self.width)
            root = Example()
            self.sync(root)
            self.assertEqual(tuple(root.children[0].children[0].ui.GetBitmap().GetSize()), (40, 20))
            root.width = 10
            self.sync(root)
            self.assertEqual(tuple(root.children[0].children[0].ui.GetBitmap().GetSize()), (10, 5))

    def test_canvas_geometry_resources_and_painter_state(self):
        bitmap = wx.Bitmap(80, 80)
        dc = wx.MemoryDC(bitmap)
        dc.SetBackground(wx.Brush(wx.WHITE))
        dc.Clear()
        canvas = Canvas(lambda c: None)
        canvas.dc = dc
        canvas.drawRect(30, 30, 10, 10, fill=0xFF0000)
        # Geometry leaves its styles active; local GraphicsContexts used by
        # curves/images must preserve those DC styles.
        original_pen, original_brush = dc.GetPen(), dc.GetBrush()
        canvas.drawCubicBezier((5, 40), (10, 30), (20, 50), (30, 40), color=0)
        resource = ImageResource()
        resource.image = wx.Image(10, 10)
        resource.image.SetRGB(wx.Rect(0, 0, 10, 10), 0, 0, 255)
        scaled = resource.crop(0, 0, 5, 5).scale(20, 10)
        self.assertEqual(tuple(scaled.image.GetSize()), (10, 10))
        canvas.drawImage(resource, 50, 50, opacity=0.5)
        self.assertFalse(resource.image.HasAlpha())
        self.assertEqual(dc.GetPen(), original_pen)
        self.assertEqual(dc.GetBrush(), original_brush)
        dc.SelectObject(wx.NullBitmap)
        image = bitmap.ConvertToImage()
        self.assertEqual((image.GetRed(15, 15), image.GetGreen(15, 15)), (255, 0))
        self.assertGreater(image.GetBlue(52, 52), image.GetRed(52, 52))
        canvas.dc = None
        recur_delete(canvas, canvas, True)
        canvas._paint(None)  # A queued paint after removal must not create a DC.

    def test_menu_reorder_callbacks_and_html(self):
        calls = []
        class Example(Application):
            actions = ['a', 'b']
            generation = 0
            def content(self):
                with Window():
                    Html('<b>native HTML</b>')
                    with MenuBar():
                        with Menu('Main'):
                            for action in self.actions:
                                MenuAction(action).id(action).trigger(calls.append, self.generation)
        root = Example()
        self.sync(root)
        frame = root.children[0]
        bar = frame.children[-1]
        self.assertIs(frame.ui.GetMenuBar(), bar.ui)
        root.actions = ['b', 'a']
        root.generation = 1
        self.sync(root)
        menu = root.children[0].children[-1].children[0]
        self.assertEqual([item.GetItemLabel() for item in menu.ui.GetMenuItems()], ['b', 'a'])
        event = wx.CommandEvent(wx.EVT_MENU.typeId, menu.children[0].ui.GetId())
        root.children[0].ui.ProcessEvent(event)
        self.assertEqual(calls, [1])
        root.actions = ['a']
        self.sync(root)
        self.assertEqual(root.children[0].ui.GetMenuBar().GetMenu(0).GetMenuItemCount(), 1)

    @patch.object(Html, '_create_webview', side_effect=RuntimeError('forced fallback'))
    def test_html_fallback_uses_its_content_size_in_layout(self, _create):
        class Example(Application):
            lines = 1
            def content(self):
                with Window(size=(320, 240)):
                    with VBox():
                        Html('<br>'.join(
                            '<i>HTML</i> <span style="color:red">support</span>'
                            for _ in range(self.lines)
                        ))
                        Spacer()

        root = Example()
        self.sync(root)
        self.pump()
        html = root.children[0].children[0].children[0].ui
        content = html.GetInternalRepresentation()
        self.assertEqual(html.ToText().strip(), 'HTML support')
        self.assertGreater(content.GetHeight(), 0)
        self.assertGreaterEqual(html.GetClientSize().height, content.GetHeight())
        initial_height = html.GetBestSize().height

        root.lines = 3
        self.sync(root)
        self.pump()
        html = root.children[0].children[0].children[0].ui
        self.assertGreater(html.GetBestSize().height, initial_height)

    def test_window_ref_dispatches_worker_calls_on_gui_thread(self):
        from threading import get_ident
        from ref_thread_helpers import call_in_thread
        import PUI.wx as UI
        class Example(Application):
            def content(self):
                Window().ref('wx-queued-window')
        root = Example()
        root.sync()
        binder = UI.ref('wx-queued-window')
        native = root.children[0].ui
        calls = []
        with patch.object(native, 'Maximize', side_effect=lambda enabled: calls.append(get_ident())):
            call_in_thread(lambda: binder.maximize(True))
            self.assertEqual(calls, [])
            root.sync()
            self.pump()
            self.assertEqual(calls, [get_ident()])
            call_in_thread(lambda: binder.maximize(False))
            recur_delete(root, root, True)
            self.pump()
            self.assertEqual(calls, [get_ident()])

    def test_window_ref_commands_follow_updates(self):
        import PUI.wx as UI
        class Example(Application):
            def content(self):
                with Window(size=(320, 240)).ref('wx-window'):
                    Label('Ref commands')
        root = Example()
        root.sync()
        self.pump()
        binder = UI.ref('wx-window')
        native = root.children[0].ui
        binder.fullscreen(True)
        self.pump()
        self.assertTrue(native.IsFullScreen())
        binder.fullscreen(False)
        self.pump()
        self.assertFalse(native.IsFullScreen())
        root.sync()
        with patch.object(native, 'IsIconized', return_value=True), \
             patch.object(native, 'Iconize') as iconize, \
             patch.object(native, 'Maximize') as maximize:
            binder.maximize(True)
            self.pump()
            maximize.assert_called_once_with(True)
            iconize.assert_called_once_with(True)
            binder.minimize(False)
            self.pump()
            self.assertEqual(iconize.call_args.args, (False,))
        recur_delete(root, root, True)
        with self.assertRaises(KeyError):
            UI.ref('wx-window')
        with self.assertRaises(RuntimeError):
            binder.minimize(False)
            self.pump()

    def test_window_flags_are_initial_declarations(self):
        class Example(Application):
            flags = True
            fluent = False
            def content(self):
                window = Window(size=(320, 240), maximize=self.flags, fullscreen=self.flags)
                if self.fluent:
                    window.maximize(not self.flags).fullscreen(not self.flags)
                with window:
                    Label('window')

        for fluent in (False, True):
            for initial in (False, True):
                with self.subTest(fluent=fluent, initial=initial):
                    root = Example()
                    root.fluent, root.flags = fluent, initial
                    with patch.object(wx.Frame, 'Maximize') as maximize:
                        self.sync(root)
                        expected = not initial if fluent else initial
                        maximize.assert_called_once_with(expected)
                        window = root.children[0]
                        native = window.ui
                        self.assertEqual(native.IsFullScreen(), expected)
                        self.assertIs(window.maximize(not expected).fullscreen(not expected), window)
                        root.flags = not initial
                        self.sync(root)
                        self.assertIs(root.children[0].ui, native)
                        self.assertEqual(native.IsFullScreen(), expected)
                        maximize.assert_called_once_with(expected)
                        native.ShowFullScreen(False)
                        self.sync(root)
                        self.assertFalse(native.IsFullScreen())
                    recur_delete(root, root, True)

    def test_nested_view_updates_on_gui_queue(self):
        @PUI
        def Child():
            Label('nested')
        class Example(Application):
            def content(self):
                with Window():
                    with VBox():
                        Child()
        root = Example()
        self.sync(root)
        child = root.children[0].children[0].children[0]
        label = child.children[0].ui
        child.redraw()
        self.pump()
        self.assertIs(child.children[0].ui, label)
        self.assertFalse(child.updating)


if __name__ == '__main__':
    unittest.main()
