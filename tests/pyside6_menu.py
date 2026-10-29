"""QT_QPA_PLATFORM=offscreen env/bin/python -m unittest discover -s tests -p pyside6_menu.py"""
import unittest
from unittest.mock import patch
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenuBar
from PUI.PySide6 import Application, Window, MenuBar, Menu, MenuAction
from PUI.dom import recur_delete


class MenuRoleTests(unittest.TestCase):
    def test_native_defaults_and_retained_updates(self):
        qt = QApplication.instance() or QApplication([])
        calls = []

        class RecordingMenuBar(QMenuBar):
            def setNativeMenuBar(self, native):
                self.requested_native = native
                super().setNativeMenuBar(native)

        class Demo(Application):
            native = None
            role = None

            def content(self):
                with Window():
                    options = {} if self.native is None else {'native': self.native}
                    with MenuBar(**options) as self.bar:
                        with Menu('File'):
                            options = {} if self.native is None else {'native': self.native}
                            self.action = MenuAction('Preferences', **options).id('preferences')
                            if self.role is not None:
                                self.configured_action = self.action.qt(role=self.role).qt()
                            self.action.trigger(calls.append, self.native)

        app = Demo()
        app.ui = qt
        patcher = patch('PUI.PySide6.menu.QtWidgets.QMenuBar', RecordingMenuBar)
        patcher.start()
        self.addCleanup(patcher.stop)
        try:
            app.sync()
            action = app.action.ui
            bar = app.bar.ui
            self.assertTrue(bar.requested_native)
            self.assertEqual(action.menuRole(), QAction.MenuRole.TextHeuristicRole)
            for native, role in ((False, QAction.MenuRole.NoRole),
                                 (True, QAction.MenuRole.TextHeuristicRole)):
                app.native = native
                app.sync()
                self.assertIs(app.bar.ui, bar)
                self.assertEqual(bar.requested_native, native)
                if not native:
                    self.assertFalse(bar.isNativeMenuBar())
                self.assertIs(app.action.ui, action)
                self.assertEqual(action.menuRole(), role)
                action.trigger()
            self.assertEqual(calls, [False, True])
            # Explicit roles override native, including the zero-valued NoRole.
            for native in (False, True):
                app.native = native
                for role in QAction.MenuRole:
                    app.role = role
                    app.sync()
                    self.assertIs(app.configured_action, app.action)
                    self.assertIs(app.action.ui, action)
                    self.assertEqual(action.menuRole(), role)
                app.role = None
                app.sync()
                expected = QAction.MenuRole.TextHeuristicRole if native else QAction.MenuRole.NoRole
                self.assertEqual(action.menuRole(), expected)
            with self.assertRaises(TypeError):
                app.action.qt(role='AboutRole')
        finally:
            recur_delete(app, app, True)
