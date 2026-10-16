"""Run with a Tk-enabled Python and display: python3 -m unittest discover -s tests -p tkinter_regression.py"""
import importlib.util
import unittest
from unittest.mock import patch

available = importlib.util.find_spec('tkinter') is not None
if available:
    from PUI.tkinter import PUI, Application, Window, HBox, VBox, Label, Button, Checkbox, RadioButton, TextField, MaskedField, DummyBinding, Tabs, Tab, Scroll, Canvas, ComboBox, ComboBoxItem, Grid, Divider
    from PUI.dom import recur_delete


@unittest.skipUnless(available, 'tkinter is not installed')
class TkinterRegression(unittest.TestCase):
    def wait_for(self, predicate):
        import time
        deadline = time.monotonic() + 1
        while not predicate() and time.monotonic() < deadline:
            self.root.ui.update()
            time.sleep(0.005)
        self.assertTrue(predicate())

    def tearDown(self):
        if hasattr(self, 'root'):
            recur_delete(self.root, self.root, True)

    def test_application_keeps_tk_default_theme(self):
        import tkinter as tk
        from tkinter import ttk
        baseline = tk.Tk()
        self.addCleanup(baseline.destroy)
        baseline.withdraw()
        default_theme = ttk.Style(baseline).theme_use()
        self.root = Application()
        self.root.sync()
        self.assertEqual(ttk.Style(self.root.ui).theme_use(), default_theme)

    def test_frame_styles_inherit_theme_after_override_removal(self):
        from tkinter import ttk
        from PUI.tkinter import Spacer

        class Example(Application):
            background = None
            def content(self):
                with Window():
                    with VBox():
                        Spacer().style(bgColor=self.background)

        self.root = Example()
        native = None
        for background in (None, 0x123456, None):
            self.root.background = background
            self.root.sync()
            spacer = self.root.children[0].children[0].children[0]
            if native is not None:
                self.assertIs(spacer.ui, native)
            native = spacer.ui
            style = ttk.Style(native)
            name = native.cget('style')
            settings = style.configure(name) or {}
            if background is None:
                self.assertNotIn('background', settings)
                for theme in ('clam', 'alt'):
                    style.theme_use(theme)
                    style.configure('TFrame', background='#234567')
                    self.assertEqual(style.lookup(name, 'background'), '#234567')
            else:
                self.assertEqual(settings['background'], '#123456')
                self.assertNotIn('foreground', settings)
                self.assertNotIn('font', settings)

    def test_classic_widgets_follow_theme_and_keep_explicit_colors(self):
        from tkinter import ttk

        class Example(Application):
            def content(self):
                with Window():
                    with VBox():
                        Label('theme')
                        Label('custom').style(bgColor=0x123456, color=0xABCDEF)
                        TextField(DummyBinding('value'))
                        with Scroll():
                            Label('scroll')

        self.root = Example().tkinter(theme='classic')
        self.root.sync()
        label, custom, field, scroll = self.root.children[0].children[0].children
        style = ttk.Style(self.root.ui)
        self.root.ui.update()
        for theme in ('clam', 'classic'):
            style.theme_use(theme)
            style.configure('TLabel', background='#345678', foreground='#abcdef')
            style.configure('TEntry', fieldbackground='#456789')
            style.configure('TFrame', background='#56789a')
            self.root.ui.update()
            self.assertEqual(str(label.ui.cget('background')), '#345678')
            self.assertEqual(str(label.ui.cget('foreground')), '#abcdef')
            self.assertEqual(str(custom.ui.cget('background')), '#123456')
            self.assertEqual(str(custom.ui.cget('foreground')), '#ABCDEF')
            self.assertIsInstance(field.ui, ttk.Entry)
            self.assertEqual(style.lookup(field.ui.cget('style'), 'fieldbackground'), '#456789')
            self.assertEqual(str(scroll.ui.canvas.cget('background')), '#56789a')

    def test_buttons_and_entries_use_themed_widgets(self):
        from tkinter import ttk

        class Example(Application):
            background = 0x123456
            def content(self):
                with Window():
                    with VBox():
                        Button('button')
                        TextField(DummyBinding('text')).style(bgColor=self.background)
                        MaskedField(DummyBinding('secret'))

        self.root = Example().tkinter(theme='classic')
        for background in (0x123456, None):
            self.root.background = background
            self.root.sync()
            button, field, masked = self.root.children[0].children[0].children
            self.assertIsInstance(button.ui, ttk.Button)
            self.assertIsInstance(field.ui, ttk.Entry)
            self.assertIsInstance(masked.ui, ttk.Entry)
            style = ttk.Style(field.ui)
            settings = style.configure(field.ui.cget('style')) or {}
            if background is None:
                self.assertNotIn('fieldbackground', settings)
            else:
                self.assertEqual(settings['fieldbackground'], '#123456')
            self.assertEqual(masked.ui.cget('show'), '*')

    def test_themed_selection_controls_preserve_models_and_reuse(self):
        from tkinter import ttk
        from PUI.tkinter import Checkbox, RadioButton
        boolean, items, mapping = DummyBinding(True), DummyBinding([]), DummyBinding({})
        choice = DummyBinding('a')
        clicks = []

        class Example(Application):
            def content(self):
                with Window():
                    with VBox():
                        for index, model in enumerate((boolean, items, mapping)):
                            Checkbox('check', model, 'value').click(lambda e: clicks.append('check'))
                        RadioButton('A', 'a', choice)
                        RadioButton('B', 'b', choice)

        self.root = Example().tkinter(theme='classic')
        self.root.sync()
        controls = self.root.children[0].children[0].children
        native = [node.ui for node in controls]
        for widget in native[:3]:
            self.assertIsInstance(widget, ttk.Checkbutton)
        for widget in native[3:]:
            self.assertIsInstance(widget, ttk.Radiobutton)
        self.assertEqual([w.instate(['selected']) for w in native], [True, False, False, True, False])
        for widget in native[:3]:
            widget.invoke()
        native[4].invoke()
        self.assertEqual((boolean.value, items.value, mapping.value, choice.value),
                         (False, ['value'], {'value': True}, 'b'))
        self.assertEqual(clicks, ['check'] * 3)
        self.root.sync()
        self.assertEqual([n.ui for n in self.root.children[0].children[0].children], native)
        self.assertEqual([w.instate(['selected']) for w in native], [False, True, True, False, True])
        for widget in native[:3]:
            widget.invoke()
        self.assertEqual((boolean.value, items.value, mapping.value), (True, [], {}))
        self.root.sync()
        self.assertEqual([w.instate(['selected']) for w in native[:3]], [True, False, False])

    def test_explicit_native_theme(self):
        from tkinter import ttk
        self.root = Application().tkinter(theme='clam')
        self.root.sync()
        style = ttk.Style(self.root.ui)
        self.assertEqual(style.theme_use(), 'clam')

    def test_setup_can_theme_only_the_application_root_once(self):
        import tkinter as tk
        from tkinter import ttk
        other_root = tk.Tk()
        self.addCleanup(other_root.destroy)
        other_root.withdraw()
        other_theme = ttk.Style(other_root).theme_use()
        observed = []

        class Example(Application):
            def setup(self):
                ttk.Style(self.ui).theme_use('clam')

            def content(self):
                observed.append(ttk.Style(self.ui).theme_use())
                with Window():
                    with Tabs():
                        with Tab('Theme'):
                            Label('Themed page')

        self.root = Example()
        self.root.sync()
        self.root.ui.update()
        style = ttk.Style(self.root.ui)
        self.assertEqual(style.theme_use(), 'clam')
        self.assertEqual(observed, ['clam'])
        self.assertEqual(ttk.Style(other_root).theme_use(), other_theme)
        # Reconciliation must preserve a theme changed after initialization.
        style.theme_use('alt')
        self.root.sync()
        self.assertEqual(style.theme_use(), 'alt')

    def test_application_title_and_explicit_window_titles(self):
        class Example(Application):
            window_title = None
            def content(self):
                with Window(title=self.window_title):
                    Label('Title')
        self.root = Example(title='Application title')
        native = None
        for title in (None, 'Document', '', None):
            self.root.window_title = title
            self.root.sync()
            window = self.root.children[0].ui
            if native is not None:
                self.assertIs(window, native)
            native = window
            self.assertEqual(window.title(), 'Application title' if title is None else title)
            self.assertEqual(self.root.ui.title(), 'Application title')

    def test_placeholder_is_accepted_without_becoming_entry_text(self):
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
                    field_type(model, edit, **self.options).input(lambda e: events.append(e.value))

        self.root = Example()
        self.root.sync()
        native = self.root.children[0].children[0].ui
        self.assertEqual(native.cget('show'), '*' if field_type is MaskedField else '')
        self.assertEqual((native.get(), model.value, edit.value), ('', '', ''))
        self.assertEqual(events, [])
        native.insert(0, 'typed')
        for options in ({'placeholder': 'Updated'}, {'placeholder': ''}, {'placeholder': None}, {}):
            self.root.options = options
            self.root.sync()
            field = self.root.children[0].children[0]
            self.assertIs(field.ui, native)
            self.assertEqual(native.cget('show'), '*' if field_type is MaskedField else '')
            self.assertEqual((native.get(), model.value, edit.value), ('typed', '', 'typed'))
            self.assertEqual(events, ['typed'])
        self.root.children[0].children[0].on_change()
        self.assertEqual(model.value, 'typed')


    def test_enabled_controls_retain_widgets_and_models(self):
        index, text = DummyBinding(1), DummyBinding('two')
        clicks, changes = [], []

        flag, choice = DummyBinding(True), DummyBinding("one")

        class Example(Application):
            options = {'enabled': False}
            def content(self):
                with Window():
                    with VBox():
                        Button('Run', **self.options).click(lambda e: clicks.append('click'))
                        for editable in (False, True):
                            with ComboBox(editable, index, text, **self.options).id(editable).change(lambda e: changes.append(e.value)):
                                ComboBoxItem('First', 'one')
                                ComboBoxItem('Second', 'two')
                        Checkbox("Check", flag, **self.options)
                        RadioButton("Radio", "two", choice, **self.options)

        self.root = Example()
        native = None
        expected_clicks = 0
        for options in ({'enabled': False}, {'enabled': True}, {'enabled': False}, {}):
            self.root.options = options
            self.root.sync()
            self.root.ui.update()
            controls = self.root.children[0].children[0].children
            if native is None:
                native = [node.ui for node in controls]
            enabled = options.get('enabled', True)
            for node, ui in zip(controls, native):
                self.assertIs(node.ui, ui)
            self.assertEqual(str(controls[0].ui.cget('state')), 'normal' if enabled else 'disabled')
            controls[0].ui.invoke()
            expected_clicks += enabled
            self.assertEqual(len(clicks), expected_clicks)
            for combo in controls[1:3]:
                expected = ('normal' if combo.editable else 'readonly') if enabled else 'disabled'
                self.assertEqual(str(combo.ui.cget('state')), expected)
                self.assertEqual(combo.ui.get(), 'Second')
            self.assertEqual((index.value, text.value), (1, 'two'))
            check, radio = controls[3:]
            for node in (check, radio):
                self.assertEqual(str(node.ui.cget('state')), 'normal' if enabled else 'disabled')
            self.assertEqual(check.var.get(), 1)
            self.assertEqual(radio.var.get(), 'one')
            check.ui.invoke()
            radio.ui.invoke()
            self.assertEqual(flag.value, not enabled)
            self.assertEqual(choice.value, 'two' if enabled else 'one')
            flag.value, choice.value = True, 'one'
            self.assertEqual(changes, [])

    def test_edit_payloads_and_programmatic_changes(self):
        model, edit = DummyBinding('initial'), DummyBinding('')
        events = []
        class Example(Application):
            def content(self):
                with Window():
                    with VBox():
                        TextField(model, edit).input(lambda e: events.append(('input', e.value))).change(lambda e: events.append(('change', e.value)))
        self.root = Example()
        self.root.sync()
        native_root = self.root.ui
        model.value = 'programmatic'
        self.root.sync()
        self.assertIs(self.root.ui, native_root)
        field = self.root.children[0].children[0].children[0]
        self.assertEqual(events, [])
        field.variable.set('typed')
        self.root.sync()
        field = self.root.children[0].children[0].children[0]
        field.on_change()
        field.on_change()
        self.assertEqual(model.value, 'typed')
        self.assertEqual(events, [('input', 'typed'), ('change', 'typed')])
        self.assertEqual(len(field.variable.trace_info()), 1)

    def test_textfield_expands_horizontally_at_native_height(self):
        class Example(Application):
            def content(self):
                with Window(size=(400, 240)):
                    with HBox():
                        TextField(DummyBinding('value'))

        self.root = Example()
        self.root.sync()
        self.root.ui.update()
        field = self.root.children[0].children[0].children[0]
        self.assertGreater(field.ui.winfo_width(), field.ui.winfo_reqwidth())
        self.assertEqual(field.ui.winfo_height(), field.ui.winfo_reqheight())
        self.assertEqual(field.ui.grid_info()['sticky'], 'ew')

    def test_redraw_coalesces_through_native_parent(self):
        self.root = Application()
        self.root.sync()
        with patch.object(self.root.ui, 'after') as after:
            for _ in range(1000):
                self.root.redraw()
        self.assertEqual(after.call_count, 1)

    def test_initial_window_flags_and_tabs_removal(self):
        class Example(Application):
            flags = True
            tabs = True
            def content(self):
                with Window(fullscreen=self.flags):
                    if self.tabs:
                        with Tabs():
                            with Tab('page'):
                                Label('inside')
                    else:
                        Label('replacement')
        self.root = Example()
        self.root.sync()
        self.root.ui.update()
        self.root.flags = False
        self.root.sync()
        self.root.ui.update()
        window = self.root.children[0]
        self.wait_for(lambda: bool(window.ui.attributes('-fullscreen')))
        window.fullscreen(False)
        self.root.ui.update()
        self.wait_for(lambda: not bool(window.ui.attributes('-fullscreen')))
        self.root.tabs = False
        self.root.sync()

    def test_scroll_mount_and_empty_bounds(self):
        class Example(Application):
            def content(self):
                with Window(size=(300, 180)):
                    with Scroll().scrollY(Scroll.END):
                        with VBox():
                            Label('content')
        self.root = Example()
        self.root.sync()
        scroll = self.root.children[0].children[0]
        self.assertIs(scroll.outer, scroll.ui.container)
        from tkinter import ttk
        self.assertIsInstance(scroll.ui.scroll_x, ttk.Scrollbar)
        self.assertIsInstance(scroll.ui.scroll_y, ttk.Scrollbar)
        with patch.object(scroll.ui.canvas, 'bbox', return_value=None):
            scroll.ui.update_scroller()
            scroll.preSync()
        self.assertFalse(scroll.ui.wheel_bindings == {})

    def test_canvas_shapes_and_text_signature(self):
        def painter(canvas):
            canvas.drawText(0, 0, 'text', size=12, color=0, rotate=15)
            canvas.drawRect(30, 30, 10, 10, fill=0xFF0000)
            canvas.drawEllipse(50, 50, 5, 10, stroke=0)
            canvas.drawPolygon([(0, 0), (5, 0), (5, 5)], fill=0)
        class Example(Application):
            def content(self):
                with Window():
                    Canvas(painter).layout(width=100, height=100)
        self.root = Example()
        self.root.sync()
        canvas = self.root.children[0].children[0]
        items = canvas.ui.find_all()
        self.assertEqual(len(items), 4)
        self.assertEqual(canvas.ui.coords(items[1]), [10.0, 10.0, 30.0, 30.0])

    def test_removed_subview_cancels_native_idle_callback(self):
        @PUI
        def Child():
            Label('child')
        class Example(Application):
            show = True
            def content(self):
                with Window():
                    with VBox():
                        if self.show:
                            Child()
        self.root = Example()
        self.root.sync()
        child = self.root.children[0].children[0].children[0]
        child.redraw()
        token = child._after_id
        self.assertIn(token, self.root.ui.tk.call('after', 'info'))
        self.root.show = False
        self.root.sync()
        self.assertNotIn(token, self.root.ui.tk.call('after', 'info'))
        self.root.ui.update()

    def test_combobox_selection_free_text_and_reuse(self):
        index, text = DummyBinding(0), DummyBinding('one')
        events = []
        class Example(Application):
            def content(self):
                with Window():
                    with ComboBox(editable=True, index_model=index, text_model=text).change(lambda e: events.append(e.value)):
                        ComboBoxItem('first', 'one')
                        ComboBoxItem('second', 'two')
        self.root = Example()
        self.root.sync()
        combo = self.root.children[0].children[0]
        combo.ui.current(1)
        combo.ui.event_generate('<<ComboboxSelected>>')
        self.root.ui.update_idletasks()
        self.assertEqual(text.value, 'two')
        self.assertEqual(events, [1])
        combo.variable.set('typed')
        self.root.ui.update_idletasks()
        self.root.sync()
        combo = self.root.children[0].children[0]
        self.assertEqual(index.value, -1)
        self.assertEqual(combo.variable.get(), 'typed')
        self.assertEqual(len(combo.variable.trace_info()), 1)

    def test_click_finishes_focused_editor_before_callback(self):
        model = DummyBinding('initial')
        seen = []
        class Example(Application):
            def content(self):
                with Window():
                    with VBox():
                        TextField(model)
                        Label('click').click(lambda e: seen.append(model.value))
        self.root = Example()
        self.root.sync()
        self.root.ui.update()
        field, label = self.root.children[0].children[0].children
        field.ui.focus_force()
        field.variable.set('edited')
        label._clicked()
        self.assertEqual(seen, ['edited'])

    def test_grid_spans_padding_replacement_and_divider(self):
        class Example(Application):
            column = 0
            def content(self):
                with Window():
                    with VBox():
                        with Grid():
                            Label('cell').grid(row=1, column=self.column, columnspan=2).layout(padding=(1, 2, 3, 4))
                        Divider()
        self.root = Example()
        self.root.sync()
        grid, divider = self.root.children[0].children[0].children
        info = grid.children[0].ui.grid_info()
        self.assertEqual((info['row'], info['columnspan']), (1, 2))
        self.assertEqual(tuple(map(int, info['padx'])), (4, 2))
        self.assertEqual(str(divider.ui.cget('orient')), 'horizontal')
        self.root.column = 2
        self.root.sync()
        grid = self.root.children[0].children[0].children[0]
        self.assertEqual(grid.ui.columnconfigure(0)['weight'], 0)
        self.assertEqual(grid.children[0].ui.grid_info()['column'], 2)

    def test_dialog_argument_filters_cancel_and_result_types(self):
        from PUI.tkinter import dialog
        self.assertEqual(dialog._filetypes('Images (*.png *.jpg);;All (*)'),
                         [('Images', ('*.png', '*.jpg')), ('All', ('*',))])
        with patch.object(dialog.filedialog, 'askopenfilenames', return_value=('a', 'b')):
            self.assertEqual(dialog.OpenFiles(dir='/tmp'), ['a', 'b'])
        with patch.object(dialog.filedialog, 'askopenfilename', return_value=''):
            self.assertIsNone(dialog.OpenFile(directory='/tmp'))
        with patch.object(dialog.filedialog, 'asksaveasfilename', return_value='result') as save:
            self.assertEqual(dialog.SaveFile('/tmp/name.txt'), 'result')
            self.assertEqual(save.call_args.kwargs['initialfile'], 'name.txt')
            self.assertEqual(save.call_args.kwargs['initialdir'], '/tmp')

    def test_native_tab_placement(self):
        from tkinter import ttk
        class Example(Application):
            def content(self):
                with Window():
                    with Tabs(tabposition=Tabs.SOUTH):
                        with Tab('page'):
                            Label('content')
        self.root = Example()
        self.root.sync()
        tabs = self.root.children[0].children[0]
        self.assertEqual(ttk.Style(tabs.ui).lookup(tabs.ui.cget('style'), 'tabposition'), 's')

    def test_geometry_idle_flush_does_not_reenter_reconciliation(self):
        class Example(Application):
            builds = 0
            def content(self):
                self.builds += 1
                with Window():
                    with Scroll():
                        Label('content')
        self.root = Example()
        self.root.sync()
        self.root.redraw()
        self.root.sync()
        self.assertEqual(self.root.builds, 2)
        self.root.ui.update()
        self.assertEqual(self.root.builds, 3)
