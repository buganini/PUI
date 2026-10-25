"""Run separately with PUI_TEST_BACKEND=PySide6, wx or tkinter."""
import contextlib
import importlib
import io
import os
import unittest
from unittest.mock import patch

from PUI import DummyBinding
from PUI.dom import recur_delete

backend = os.environ.get('PUI_TEST_BACKEND', 'PySide6')
UI = importlib.import_module('PUI.' + backend)


class TextEditNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if backend == 'PySide6':
            from PySide6 import QtWidgets
            cls.native = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        elif backend == 'wx':
            import wx
            cls.native = wx.GetApp() or wx.App()

    def setUp(self):
        self.model, self.draft = DummyBinding(''), DummyBinding('')
        self.events = []
        owner = self
        class App(UI.Application):
            readonly = False
            wrap = True
            placeholder = 'Enter text'
            def content(self):
                with UI.Window(size=(500, 300)):
                    with UI.VBox():
                        self.editor = UI.TextEdit(owner.model, owner.draft,
                            readonly=self.readonly, wrap=self.wrap, placeholder=self.placeholder)
                        self.editor.input(lambda e: owner.events.append(('input', e.value)))
                        self.editor.change(lambda e: owner.events.append(('change', e.value)))
                        self.button = UI.Button('Other control').click(
                            lambda event: owner.events.append(('click', owner.model.value)))
        self.root = App()
        if backend == 'PySide6':
            self.root.ui = self.native
        self.sync()

    def tearDown(self):
        recur_delete(self.root, self.root, True)
        if backend != 'tkinter':
            self.pump()

    def pump(self):
        for _ in range(5):
            if backend == 'PySide6':
                self.native.processEvents()
            elif backend == 'wx':
                self.native.Yield()
                self.native.ProcessPendingEvents()
            else:
                self.root.ui.update()

    def sync(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.root.sync()
            self.pump()
        self.assertNotIn('<ERROR', output.getvalue())

    def append(self, value):
        widget = self.root.editor.ui
        if backend == 'PySide6':
            widget.insertPlainText(value)
        elif backend == 'wx':
            widget.WriteText(value)
        else:
            widget.insert('end', value)
        self.pump()

    def value(self):
        widget = self.root.editor.ui
        return (widget.toPlainText() if backend == 'PySide6' else
                widget.GetValue() if backend == 'wx' else widget.get('1.0', 'end-1c'))

    def blur(self):
        widget = self.root.editor.ui
        if backend == 'PySide6':
            from PySide6 import QtCore, QtGui
            self.native.sendEvent(widget, QtGui.QFocusEvent(QtCore.QEvent.FocusOut))
        elif backend == 'wx':
            import wx
            event = wx.FocusEvent(wx.wxEVT_KILL_FOCUS, widget.GetId())
            widget.GetEventHandler().ProcessEvent(event)
        else:
            widget.event_generate('<FocusOut>')
        self.pump()

    def test_draft_commit_once_and_retained_widget(self):
        widget = self.root.editor.ui
        self.assertEqual(self.events, [])
        self.append('first\n中文')
        self.assertEqual(self.model.value, '')
        self.assertEqual(self.draft.value, 'first\n中文')
        self.root.placeholder, self.root.wrap = 'Changed hint', False
        self.sync()
        self.assertIs(self.root.editor.ui, widget)
        self.assertEqual(self.value(), 'first\n中文')
        self.model.value = 'external update during editing'
        self.sync()
        self.assertEqual(self.value(), 'first\n中文')
        self.blur()
        self.blur()
        self.assertEqual(self.model.value, 'first\n中文')
        self.assertEqual([e for e in self.events if e[0] == 'change'], [('change', 'first\n中文')])
        self.model.value = 'programmatic\nreplacement'
        previous = list(self.events)
        self.sync()
        self.assertEqual(self.value(), self.model.value)
        self.assertEqual(self.draft.value, self.model.value)
        self.assertEqual(self.events, previous)

    def test_readonly_and_programmatic_updates(self):
        self.root.readonly = True
        self.model.value = 'read only\ntext'
        self.sync()
        self.root.editor._input_text('unexpected input')
        self.blur()
        self.assertEqual(self.model.value, 'read only\ntext')
        self.assertEqual(self.events, [])
        self.model.value = 'updated'
        self.sync()
        self.assertEqual(self.value(), 'updated')
        self.root.readonly = False
        self.sync()
        self.append('!')
        self.blur()
        self.assertIn('!', self.model.value)

    def test_control_click_commits_before_callback(self):
        widget = self.root.editor.ui
        if backend == 'PySide6':
            self.root.children[0].ui.activateWindow()
            widget.setFocus()
        elif backend == 'wx':
            widget.SetFocus()
        else:
            widget.focus_force()
        self.pump()
        self.append('pending\ntext')
        if backend == 'wx':
            # A background macOS test process cannot activate a native window.
            # Supply only focus lookup; use the real editor and click dispatch.
            with patch('wx.Window.FindFocus', return_value=widget):
                self.root.button._clicked()
        else:
            self.root.button._clicked()
        self.pump()
        self.assertEqual(self.events[-1], ('click', 'pending\ntext'))

    @unittest.skipUnless(backend == 'PySide6', 'Qt keyboard and IME test')
    def test_enter_ime_and_selection_survive_redraw(self):
        from PySide6 import QtCore, QtGui, QtTest
        widget = self.root.editor.ui
        widget.setFocus()
        QtTest.QTest.keyClicks(widget, 'hello')
        QtTest.QTest.keyClick(widget, QtCore.Qt.Key_Return)
        self.assertEqual(self.draft.value, 'hello\n')
        self.assertEqual(self.model.value, '')
        ime = QtGui.QInputMethodEvent('中', [])
        self.native.sendEvent(widget, ime)
        self.assertEqual(self.draft.value, 'hello\n')
        ime = QtGui.QInputMethodEvent()
        ime.setCommitString('中')
        self.native.sendEvent(widget, ime)
        self.assertEqual(self.draft.value, 'hello\n中')
        cursor = widget.textCursor()
        cursor.setPosition(1)
        cursor.setPosition(4, QtGui.QTextCursor.KeepAnchor)
        widget.setTextCursor(cursor)
        previous = list(self.events)
        self.sync()
        self.assertEqual(widget.textCursor().selectedText(), 'ell')
        self.assertEqual(self.events, previous)
