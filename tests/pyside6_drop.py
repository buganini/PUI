import unittest
from PySide6 import QtCore, QtGui, QtWidgets
import PUI.PySide6 as UI
from PUI.PySide6.drop import handle


class DropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_native_enter_drop_actions_and_explicit_rejection(self):
        mime=QtCore.QMimeData();mime.setText('hello')
        received=[]
        class App(UI.Application):
            def content(self):
                with UI.Window():
                    self.target=UI.Label('drop').drop(lambda e:(received.append(e),e.accept()))
        app=App();app.ui=self.app;app.sync()
        try:
            enter=QtGui.QDragEnterEvent(QtCore.QPoint(1,2),QtCore.Qt.CopyAction,mime,QtCore.Qt.LeftButton,QtCore.Qt.NoModifier)
            handle(app.target,enter,entering=True)
            self.assertTrue(enter.isAccepted())
            for native,action in ((QtCore.Qt.CopyAction,'copy'),(QtCore.Qt.MoveAction,'move'),(QtCore.Qt.LinkAction,'link')):
                event=QtGui.QDropEvent(QtCore.QPointF(1,2),native,mime,QtCore.Qt.LeftButton,QtCore.Qt.NoModifier)
                handle(app.target,event)
                self.assertTrue(event.isAccepted())
                self.assertEqual((received[-1].text,received[-1].action),('hello',action))
            app.target.drop(lambda e:None)
            event=QtGui.QDropEvent(QtCore.QPointF(1,2),QtCore.Qt.CopyAction,mime,QtCore.Qt.LeftButton,QtCore.Qt.NoModifier)
            handle(app.target,event)
            self.assertFalse(event.isAccepted())
        finally:
            for widget in self.app.topLevelWidgets():widget.close()
