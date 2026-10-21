"""QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p pyside6_regression.py"""
import importlib.util
import unittest

available = importlib.util.find_spec('PySide6') is not None
if available:
    from PUI.PySide6 import Application, Window, Modal, VBox, Label, Button, Checkbox, RadioButton, TextField, MaskedField, DummyBinding, ComboBox, ComboBoxItem, ProgressBar, Side, Tabs, Tab
    from PUI.dom import recur_delete
    from PUI.PySide6.base import _apply_params
    from PySide6 import QtCore, QtWidgets


@unittest.skipUnless(available, 'PySide6 is not installed')
class PySide6Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def tearDown(self):
        for widget in self.app.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        self.app.processEvents()

    def test_adaptive_box_retains_editor(self):
        from PUI.PySide6 import HVBox, VHBox
        class Example(Application):
            def content(self):
                with Window(size=(800, 500)):
                    with VBox().layout(weight=1) as parent:
                        with HVBox(600) as box:
                            TextField(DummyBinding('retained'))
                        with VHBox(350):
                            Label('second')
        root = Example()
        root.ui = self.app
        root.sync()
        for _ in range(12): self.app.processEvents()
        parent = root.children[0].children[0]
        editor = parent.children[0].children[0].ui
        layout = parent.children[0].qtlayout
        for width in (500,800,500,800):
            root.children[0].ui.resize(width,500)
            for _ in range(12): self.app.processEvents()
            box = parent.get_node().children[0]
            self.assertIs(box.children[0].ui, editor)
            self.assertIs(box.qtlayout, layout)
            expected = QtWidgets.QBoxLayout.LeftToRight if width>=600 else QtWidgets.QBoxLayout.TopToBottom
            self.assertEqual(layout.direction(), expected)

    def test_adaptive_size_and_breakpoints(self):
        class Example(Application):
            def content(self):
                with Window(size=(800, 400)):
                    with VBox().layout(weight=1).id('adaptive') as container:
                        self.binding = container.size()
                        with VBox().visible(minWidth=600):
                            Label('wide')
                        with VBox().visible(maxWidth=600):
                            Label('compact')
        root = Example()
        root.ui = self.app
        root.sync()
        for _ in range(12): self.app.processEvents()
        original = root.children[0].children[0]._state
        self.assertIsNotNone(root.binding.value)
        for width in (500, 800, 500, 800):
            root.children[0].ui.resize(width, 400)
            for _ in range(12): self.app.processEvents()

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
        root.ui = self.app
        native = None
        for shown in (True, False, True, False, True):
            root.shown = shown
            root.sync()
            self.app.processEvents()
            box = root.children[0].children[0].children[1]
            if native is None:
                native = box.ui
            self.assertIs(box.ui, native)
            self.assertEqual(not box.outer.isHidden(), shown)
            self.assertTrue(box.children[1].ui.isHidden())
            parent = root.children[0].children[0]
            self.assertEqual(parent.qtlayout.itemAt(1).isEmpty(), not shown)

    def test_window_ref_dispatches_worker_calls_on_gui_thread(self):
        from threading import get_ident
        from unittest.mock import patch
        from ref_thread_helpers import call_in_thread
        import PUI.PySide6 as UI
        class Example(Application):
            def content(self):
                Window().ref('qt-queued-window')
        root = Example()
        root.ui = self.app
        try:
            root.sync()
            binder = UI.ref('qt-queued-window')
            native = root.children[0].ui
            calls = []
            with patch.object(native, 'setWindowState', side_effect=lambda flags: calls.append(get_ident())):
                call_in_thread(lambda: binder.maximize(True))
                self.assertEqual(calls, [])
                root.sync()  # Queued work must follow reconciliation.
                self.app.processEvents()
                self.assertEqual(calls, [get_ident()])
                call_in_thread(lambda: binder.fullscreen(True))
                recur_delete(root, root, True)
                self.app.processEvents()
                self.assertEqual(calls, [get_ident()])
        finally:
            if not root.destroyed:
                recur_delete(root, root, True)

    def test_window_ref_commands_preserve_other_state_bits(self):
        import PUI
        import PUI.PySide6 as UI
        self.assertIs(UI.ref, PUI.ref)
        class Example(Application):
            def content(self):
                with Window().ref('qt-window'):
                    Label('Ref commands')
        root = Example()
        root.ui = self.app
        try:
            root.sync()
            binder = UI.ref('qt-window')
            native = root.children[0].ui
            binder.maximize(True)
            binder.minimize(True)
            self.app.processEvents()
            self.assertTrue(native.isMaximized())
            self.assertTrue(native.isMinimized())
            root.sync()
            binder.minimize(False)
            self.app.processEvents()
            self.assertTrue(native.isMaximized())
            self.assertFalse(native.isMinimized())
            binder.fullscreen(True)
            binder.fullscreen(False)
            self.app.processEvents()
            self.assertTrue(native.isMaximized())
            binder.maximize(False)
            self.app.processEvents()
            self.assertFalse(native.isMaximized())
        finally:
            recur_delete(root, root, True)
        with self.assertRaises(KeyError):
            UI.ref('qt-window')
        with self.assertRaises(RuntimeError):
            binder.maximize(True)

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
        root.ui = self.app
        root.sync()
        native = root.children[0].children[0].ui
        self.assertEqual(native.echoMode(), QtWidgets.QLineEdit.EchoMode.Password if field_type is MaskedField else QtWidgets.QLineEdit.EchoMode.Normal)
        self.assertEqual(native.placeholderText(), 'Enter text')
        self.assertEqual((native.text(), model.value, edit.value), ('', '', ''))
        self.assertEqual(events, [])
        native.insert('typed')
        native.setCursorPosition(2)
        for options in ({'placeholder': 'Updated'}, {'placeholder': ''}, {'placeholder': None}, {}):
            root.options = options
            root.sync()
            self.assertIs(root.children[0].children[0].ui, native)
            self.assertEqual(native.echoMode(), QtWidgets.QLineEdit.EchoMode.Password if field_type is MaskedField else QtWidgets.QLineEdit.EchoMode.Normal)
            self.assertEqual(native.placeholderText(), options.get('placeholder') or '')
            self.assertEqual((native.text(), model.value, edit.value), ('typed', '', 'typed'))
            self.assertEqual(native.cursorPosition(), 2)
            self.assertEqual(events, [('input', 'typed')])
        native.editingFinished.emit()
        self.assertEqual(model.value, 'typed')
        self.assertEqual(events, [('input', 'typed'), ('change', 'typed')])

    def test_application_title_and_explicit_window_titles(self):
        class Example(Application):
            window_title = None
            def content(self):
                with Window(title=self.window_title):
                    Label('Title')
        original = self.app.applicationDisplayName()
        root = Example(title='Application title')
        root.ui = self.app
        try:
            native = None
            for title in (None, 'Document', '', None):
                root.window_title = title
                root.sync()
                window = root.children[0].ui
                if native is not None:
                    self.assertIs(window, native)
                native = window
                self.assertEqual(window.windowTitle(), 'Application title' if title is None else title)
                self.assertEqual(self.app.applicationDisplayName(), 'Application title')
        finally:
            self.app.setApplicationDisplayName(original)

    def test_window_flags_are_initial_declarations(self):
        self.check_initial_window_flags(Window)

    def test_modal_flags_are_initial_declarations(self):
        self.check_initial_window_flags(Modal, DummyBinding(True))

    def check_initial_window_flags(self, window_type, *args):
        class Example(Application):
            flags = True
            def content(self):
                if self.fluent:
                    window = window_type(*args, maximize=not self.flags, fullscreen=not self.flags)
                    window.maximize(self.flags).fullscreen(self.flags)
                else:
                    window = window_type(*args, maximize=self.flags, fullscreen=self.flags)
                with window:
                    Label('window')

        for fluent in (False, True):
            for initial in (False, True):
                with self.subTest(fluent=fluent, initial=initial):
                    if args:
                        args[0].value = True
                    root = Example()
                    root.fluent, root.flags = fluent, initial
                    root.ui = self.app
                    try:
                        root.sync()
                        window = root.children[0]
                        native = window.ui
                        for flag in (QtCore.Qt.WindowState.WindowMaximized,
                                     QtCore.Qt.WindowState.WindowFullScreen):
                            self.assertEqual(bool(native.windowState() & flag), initial)
                        flags = native.windowState()
                        self.assertIs(window.maximize(not initial).fullscreen(not initial), window)
                        self.assertEqual(native.windowState(), flags)
                        root.flags = not initial
                        root.sync()
                        self.assertIs(root.children[0].ui, native)
                        self.assertEqual(native.windowState(), flags)
                        # Native/user changes survive an otherwise identical declaration.
                        native.setWindowState(QtCore.Qt.WindowState(0))
                        root.sync()
                        self.assertEqual(native.windowState(), QtCore.Qt.WindowState(0))
                    finally:
                        recur_delete(root, root, True)

    def test_disabled_controls_retain_widgets_and_models(self):
        index, text = DummyBinding(0), DummyBinding('one')
        clicks, changes = [], []

        flag, choice = DummyBinding(True), DummyBinding("one")

        class Example(Application):
            options = {'disabled': True}
            def content(self):
                with Window():
                    with VBox():
                        Button('Run', **self.options).click(lambda e: clicks.append('click'))
                        for editable in (False, True):
                            with ComboBox(editable, index_model=index, text_model=text, **self.options).id(editable).change(lambda e: changes.append(e.value)):
                                ComboBoxItem('First', 'one')
                                ComboBoxItem('Second', 'two')
                        Checkbox("Check", flag, **self.options)
                        RadioButton("Radio", "two", choice, **self.options)

        root = Example()
        root.ui = self.app
        native = None
        expected_clicks = 0
        for options in ({'disabled': True}, {'disabled': False}, {'disabled': True}, {}):
            root.options = options
            index.value, text.value = 1, 'two'
            root.sync()
            controls = root.children[0].children[0].children
            if native is None:
                native = [node.ui for node in controls]
            enabled = not options.get('disabled', False)
            for node, ui in zip(controls, native):
                self.assertIs(node.ui, ui)
                self.assertEqual(ui.isEnabled(), enabled)
            controls[0].ui.click()
            expected_clicks += enabled
            self.assertEqual(len(clicks), expected_clicks)
            for combo in controls[1:3]:
                self.assertEqual(combo.ui.currentText(), 'Second')
                self.assertEqual(combo.ui.isEditable(), combo.editable)
            self.assertEqual((index.value, text.value), (1, 'two'))
            check, radio = controls[3:]
            self.assertTrue(check.ui.isChecked())
            self.assertFalse(radio.ui.isChecked())
            check.ui.click()
            radio.ui.click()
            self.assertEqual(flag.value, not enabled)
            self.assertEqual(choice.value, 'two' if enabled else 'one')
            flag.value, choice.value = True, 'one'
            self.assertEqual(changes, [])

    def test_native_autocomplete_can_be_toggled_without_replacing_editor(self):
        text = DummyBinding('Tai')
        class Example(Application):
            completion = True
            def content(self):
                with Window():
                    with ComboBox(editable=True, text_model=text, autoexpand=self.completion):
                        ComboBoxItem('Taipei')
                        ComboBoxItem('Tokyo')
        root = Example()
        root.ui = self.app
        root.sync()
        combo = root.children[0].children[0].ui
        for enabled in (True, False, True):
            root.completion = enabled
            root.sync()
            self.assertIs(root.children[0].children[0].ui, combo)
            self.assertEqual(combo.currentText(), 'Tai')
            if enabled:
                self.assertIsNotNone(combo.completer())
                root.children[0].children[0]._complete('ta')
                self.assertEqual(combo.completer().completionCount(), 2)
            else:
                self.assertIsNone(combo.completer())

    def test_autocomplete_typing_lists_all_matches_without_inserting_first(self):
        from PySide6 import QtTest
        text = DummyBinding('')
        class Example(Application):
            def content(self):
                with Window(size=(500, 300)):
                    with ComboBox(editable=True, text_model=text):
                        ComboBoxItem('Taipei Taoyuan', 'TPE')
                        ComboBoxItem('Taipei Songshan', 'TSA')
                        ComboBoxItem('Tokyo Haneda', 'HND')
                        ComboBoxItem('Tokyo Narita', 'NRT')
                        ComboBoxItem('Amsterdam', 'AMS')
        root = Example()
        root.ui = self.app
        root.sync()
        window = root.children[0].ui
        combo = root.children[0].children[0].ui
        window.show()
        window.activateWindow()
        combo.setFocus()
        QtTest.QTest.qWait(50)
        QtTest.QTest.keyClicks(combo.lineEdit(), 't')
        QtTest.QTest.qWait(30)
        self.assertEqual(combo.currentText(), 't')
        self.assertEqual(text.value, 't')
        completer = combo.completer()
        self.assertTrue(completer.popup().isVisible())
        model = completer.completionModel()
        self.assertEqual([model.index(i, 0).data() for i in range(model.rowCount())],
                         ['Taipei Taoyuan', 'Taipei Songshan', 'Tokyo Haneda', 'Tokyo Narita', 'Amsterdam'])
        QtTest.QTest.keyClick(completer.popup(), QtCore.Qt.Key.Key_Down)
        QtTest.QTest.keyClick(completer.popup(), QtCore.Qt.Key.Key_Return)
        QtTest.QTest.qWait(30)
        self.assertEqual(combo.currentText(), 'Taipei Taoyuan')
        self.assertEqual(text.value, 'TPE')
        combo.lineEdit().selectAll()
        QtTest.QTest.keyClicks(combo.lineEdit(), 'hAn')
        QtTest.QTest.qWait(30)
        self.assertEqual(combo.currentText(), 'hAn')
        self.assertEqual(text.value, 'hAn')
        self.assertTrue(completer.popup().isVisible())
        model = completer.completionModel()
        self.assertEqual([model.index(i, 0).data() for i in range(model.rowCount())],
                         ['Taipei Taoyuan', 'Taipei Songshan', 'Tokyo Haneda', 'Tokyo Narita', 'Amsterdam'])
        combo.lineEdit().selectAll()
        QtTest.QTest.keyClicks(combo.lineEdit(), 'tai tok')
        QtTest.QTest.qWait(30)
        self.assertEqual(combo.currentText(), 'tai tok')
        self.assertEqual(text.value, 'tai tok')
        self.assertEqual(completer.model().rowCount(), 5)


    def test_input_callback_survives_candidate_updates(self):
        import gc
        text = DummyBinding('')
        calls = []
        class Example(Application):
            labels = ['Taipei', 'Tokyo', 'Amsterdam']
            def content(self):
                with Window():
                    with ComboBox(editable=True, text_model=text, autoexpand=False).input(
                            lambda event: calls.append(event.value)):
                        for label in self.labels:
                            ComboBoxItem(label)
        root = Example()
        root.ui = self.app
        root.sync()
        editor = root.children[0].children[0].ui.lineEdit()
        for labels in (['Tokyo'], ['Taipei', 'Tokyo'], [], ['Amsterdam']):
            root.labels = labels
            root.sync()
            gc.collect()
            editor.textEdited.emit('query')
        self.assertEqual(calls, ['query'] * 4)

    def test_negative_combo_index_is_not_last_item(self):
        index, text = DummyBinding(-1), DummyBinding('value')
        class Example(Application):
            def content(self):
                with Window():
                    with ComboBox(index_model=index, text_model=text):
                        ComboBoxItem('first', 'one')
                        ComboBoxItem('last', 'two')
        root = Example()
        root.ui = self.app
        root.sync()
        combo = root.children[0].children[0]
        self.assertEqual(combo.ui.currentIndex(), -1)
        combo.on_currentIndexChanged(-1)
        self.assertEqual(text.value, '')

    def test_size_policy_copy_is_applied(self):
        node = Label('test').qt(HorizontalPolicy=QtWidgets.QSizePolicy.Policy.Expanding)
        widget = QtWidgets.QLabel('test')
        _apply_params(widget, node)
        self.assertEqual(widget.sizePolicy().horizontalPolicy(), QtWidgets.QSizePolicy.Policy.Expanding)

    def test_fractional_progress_range_is_native_integer(self):
        class Example(Application):
            def content(self):
                with Window():
                    ProgressBar(0.125, maximum=0.25)
        root = Example()
        root.ui = self.app
        root.sync()
        gauge = root.children[0].children[0].ui
        self.assertEqual(gauge.maximum(), 25)
        self.assertEqual(gauge.value(), 12)

    def test_editable_combo_with_both_models_preserves_free_text(self):
        index, text = DummyBinding(0), DummyBinding('one')
        draft = DummyBinding('')
        class Example(Application):
            def content(self):
                with Window():
                    with ComboBox(editable=True, index_model=index, text_model=text, edit_model=draft):
                        ComboBoxItem('first', 'one')
        root = Example()
        root.ui = self.app
        root.sync()
        root.children[0].children[0].ui.setEditText('typed')
        root.children[0].children[0]._text_edited('typed')
        root.sync()
        self.assertEqual(index.value, -1)
        self.assertEqual(text.value, 'typed')
        self.assertEqual(root.children[0].children[0].ui.currentText(), 'typed')
        self.assertEqual(draft.value, 'typed')

    def test_native_tab_placement(self):
        class Example(Application):
            position = Side.Bottom
            def content(self):
                with Window():
                    with Tabs(tabposition=self.position):
                        with Tab('page'):
                            Label('content')
        root = Example()
        root.ui = self.app
        root.sync()
        self.assertEqual(root.children[0].children[0].ui.tabPosition(), QtWidgets.QTabWidget.TabPosition.South)
        root.position = Side.Left
        root.sync()
        self.assertEqual(root.children[0].children[0].ui.tabPosition(), QtWidgets.QTabWidget.TabPosition.West)

    def test_content_size_hint_does_not_resize_the_window(self):
        class Example(Application):
            text = 'short'
            def content(self):
                with Window(size=(320, 240)):
                    with VBox():
                        Label(self.text)

        root = Example()
        root.ui = self.app
        root.sync()
        self.app.processEvents()
        window = root.children[0].ui
        self.assertEqual(window.size().toTuple(), (320, 240))

        # An unbroken label has a minimum size hint wider than the window.
        # It must be laid out inside the window instead of enlarging the
        # top-level native window beyond the screen.
        root.text = 'x' * 1000
        root.sync()
        self.app.processEvents()
        self.app.processEvents()
        self.assertGreater(window.centralWidget().minimumSizeHint().width(), 320)
        self.assertEqual(window.size().toTuple(), (320, 240))
