"""Run with a Tk-enabled Python and display: python3 -m unittest discover -s tests -p tkinter_regression.py"""
import importlib.util
import unittest
from unittest.mock import patch

available = importlib.util.find_spec('tkinter') is not None
if available:
    from PUI.tkinter import PUI, Application, Window, HBox, VBox, Label, Button, TextField, DummyBinding, Tabs, Tab, Scroll, Canvas, ComboBox, ComboBoxItem, Grid, Divider
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
        model, edit = DummyBinding(''), DummyBinding('')
        events = []

        class Example(Application):
            options = {'placeholder': 'Enter text'}
            def content(self):
                with Window():
                    TextField(model, edit, **self.options).input(lambda e: events.append(e.value))

        self.root = Example()
        self.root.sync()
        native = self.root.children[0].children[0].ui
        self.assertEqual((native.get(), model.value, edit.value), ('', '', ''))
        self.assertEqual(events, [])
        native.insert(0, 'typed')
        for options in ({'placeholder': 'Updated'}, {'placeholder': ''}, {'placeholder': None}, {}):
            self.root.options = options
            self.root.sync()
            field = self.root.children[0].children[0]
            self.assertIs(field.ui, native)
            self.assertEqual((native.get(), model.value, edit.value), ('typed', '', 'typed'))
            self.assertEqual(events, ['typed'])

    def test_enabled_controls_retain_widgets_and_models(self):
        index, text = DummyBinding(1), DummyBinding('two')
        clicks, changes = [], []

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
            for combo in controls[1:]:
                expected = ('normal' if combo.editable else 'readonly') if enabled else 'disabled'
                self.assertEqual(str(combo.ui.cget('state')), expected)
                self.assertEqual(combo.ui.get(), 'Second')
            self.assertEqual((index.value, text.value), (1, 'two'))
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
