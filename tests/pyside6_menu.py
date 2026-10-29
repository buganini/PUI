"""QT_QPA_PLATFORM=offscreen env/bin/python -m unittest discover -s tests -p pyside6_menu.py"""
import unittest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication
from PUI.PySide6 import Application, Window, MenuBar, Menu, MenuAction
from PUI.dom import recur_delete


class MenuRoleTests(unittest.TestCase):
    def test_default_opt_in_and_retained_role_updates(self):
        qt = QApplication.instance() or QApplication([])
        calls = []

        class Demo(Application):
            native = None

            def content(self):
                with Window():
                    with MenuBar():
                        with Menu('File'):
                            options = {} if self.native is None else {'native': self.native}
                            self.action = MenuAction('Preferences', **options).id('preferences')
                            self.action.trigger(calls.append, self.native)

        app = Demo()
        app.ui = qt
        try:
            app.sync()
            action = app.action.ui
            self.assertEqual(action.menuRole(), QAction.MenuRole.NoRole)
            for native, role in ((True, QAction.MenuRole.TextHeuristicRole),
                                 (False, QAction.MenuRole.NoRole)):
                app.native = native
                app.sync()
                self.assertIs(app.action.ui, action)
                self.assertEqual(action.menuRole(), role)
                action.trigger()
            self.assertEqual(calls, [True, False])
        finally:
            recur_delete(app, app, True)
