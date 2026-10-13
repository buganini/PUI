"""QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p pyside6_regression.py"""
import importlib.util
import unittest

available = importlib.util.find_spec('PySide6') is not None
if available:
    from PUI.PySide6 import Application, Window, VBox, Label, Button, TextField, DummyBinding, ComboBox, ComboBoxItem, ProgressBar, Tabs, Tab
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

    def test_placeholder_updates_preserve_edit_buffer_and_signals(self):
        model, edit = DummyBinding(''), DummyBinding('')
        events = []

        class Example(Application):
            options = {'placeholder': 'Enter text'}
            def content(self):
                with Window():
                    TextField(model, edit, **self.options).input(lambda e: events.append(('input', e.value))).change(lambda e: events.append(('change', e.value)))

        root = Example()
        root.ui = self.app
        root.sync()
        native = root.children[0].children[0].ui
        self.assertEqual(native.placeholderText(), 'Enter text')
        self.assertEqual((native.text(), model.value, edit.value), ('', '', ''))
        self.assertEqual(events, [])
        native.insert('typed')
        native.setCursorPosition(2)
        for options in ({'placeholder': 'Updated'}, {'placeholder': ''}, {'placeholder': None}, {}):
            root.options = options
            root.sync()
            self.assertIs(root.children[0].children[0].ui, native)
            self.assertEqual(native.placeholderText(), options.get('placeholder') or '')
            self.assertEqual((native.text(), model.value, edit.value), ('typed', '', 'typed'))
            self.assertEqual(native.cursorPosition(), 2)
            self.assertEqual(events, [('input', 'typed')])
        native.editingFinished.emit()
        self.assertEqual(model.value, 'typed')
        self.assertEqual(events, [('input', 'typed'), ('change', 'typed')])

    def test_initial_window_flags_and_imperative_changes(self):
        class Example(Application):
            maximize = True
            fullscreen = True
            def content(self):
                with Window(size=(320, 240), maximize=self.maximize, fullscreen=self.fullscreen):
                    Label('window')
        root = Example()
        # Reuse the existing QApplication in this test harness.
        root.ui = self.app
        root.sync()
        root.maximize = root.fullscreen = False
        root.sync()
        window = root.children[0]
        self.assertTrue(window.ui.windowState() & QtCore.Qt.WindowState.WindowFullScreen)
        window.fullscreen(False).maximize(False)
        flags = window.ui.windowState()
        self.assertFalse(flags & QtCore.Qt.WindowState.WindowMaximized)
        self.assertFalse(flags & QtCore.Qt.WindowState.WindowFullScreen)

    def test_enabled_controls_retain_widgets_and_models(self):
        index, text = DummyBinding(0), DummyBinding('one')
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

        root = Example()
        root.ui = self.app
        native = None
        expected_clicks = 0
        for options in ({'enabled': False}, {'enabled': True}, {'enabled': False}, {}):
            root.options = options
            index.value, text.value = 1, 'two'
            root.sync()
            controls = root.children[0].children[0].children
            if native is None:
                native = [node.ui for node in controls]
            enabled = options.get('enabled', True)
            for node, ui in zip(controls, native):
                self.assertIs(node.ui, ui)
                self.assertEqual(ui.isEnabled(), enabled)
            controls[0].ui.click()
            expected_clicks += enabled
            self.assertEqual(len(clicks), expected_clicks)
            for combo in controls[1:]:
                self.assertEqual(combo.ui.currentText(), 'Second')
                self.assertEqual(combo.ui.isEditable(), combo.editable)
            self.assertEqual((index.value, text.value), (1, 'two'))
            self.assertEqual(changes, [])

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
        class Example(Application):
            def content(self):
                with Window():
                    with ComboBox(editable=True, index_model=index, text_model=text):
                        ComboBoxItem('first', 'one')
        root = Example()
        root.ui = self.app
        root.sync()
        root.children[0].children[0].ui.setEditText('typed')
        root.sync()
        self.assertEqual(index.value, -1)
        self.assertEqual(text.value, 'typed')
        self.assertEqual(root.children[0].children[0].ui.currentText(), 'typed')

    def test_native_tab_placement(self):
        class Example(Application):
            position = Tabs.SOUTH
            def content(self):
                with Window():
                    with Tabs(tabposition=self.position):
                        with Tab('page'):
                            Label('content')
        root = Example()
        root.ui = self.app
        root.sync()
        self.assertEqual(root.children[0].children[0].ui.tabPosition(), QtWidgets.QTabWidget.TabPosition.South)
        root.position = Tabs.WEST
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
