"""Native Canvas sizing; run each backend separately with PUI_TEST_BACKEND.

PUI_TEST_BACKEND=wx PYTHONPATH=tests:. python -m unittest canvas_sizing
"""
import importlib
import os
import unittest


class CanvasSizingTests(unittest.TestCase):
    def test_desired_minimum_and_retained_resize(self):
        self.check_sizing('Canvas')

    def test_matplotlib_desired_minimum_and_retained_resize(self):
        self.check_sizing('MatplotlibCanvas')

    def check_sizing(self, component):
        backend = os.environ.get('PUI_TEST_BACKEND', 'PySide6')
        UI = importlib.import_module('PUI.' + backend)
        from PUI.dom import recur_delete
        if backend == 'PySide6':
            from PySide6.QtWidgets import QApplication
            native = QApplication.instance() or QApplication([])
        elif backend == 'wx':
            import wx
            native = wx.GetApp() or wx.App(False)
        class Demo(UI.Application):
            axis = 'HBox'
            params = {}
            def content(self):
                with UI.Window(size=(640, 420)) as self.window:
                    with getattr(UI, self.axis)().layout(padding=0) as self.box:
                        self.canvas = getattr(UI, component)(lambda c: None).layout(padding=0, **self.params)
        app = Demo()
        if backend == 'PySide6':
            app.ui = native
        self.addCleanup(recur_delete, app, app, True)
        def pump():
            for _ in range(5):
                if backend == 'PySide6': native.processEvents()
                elif backend == 'wx': native.Yield(); native.ProcessPendingEvents()
                else: app.ui.update()
        def size(node):
            if backend == 'PySide6': return (node.ui.size().width(), node.ui.size().height())
            if backend == 'wx': return tuple(node.ui.GetSize())
            return (node.ui.winfo_width(), node.ui.winfo_height())
        cases = [{}, {'weight': 1}, {'width': 160}, {'height': 100}, {'width': 160, 'height': 100},
                 {'minWidth': 160, 'minHeight': 100},
                 {'width': 120, 'height': 80, 'minWidth': 160, 'minHeight': 100},
                 {'width': 160, 'height': 100, 'weight': 1}, {}]
        for axis in ('HBox', 'VBox'):
            for params in cases:
                with self.subTest(backend=backend, axis=axis, params=params):
                    app.axis, app.params = axis, params
                    app.sync(); pump()
                    for target in ((640, 420), (880, 560)):
                        if backend == 'PySide6': app.window.ui.resize(*target)
                        elif backend == 'wx': app.window.ui.SetClientSize(target); app.window.ui.Layout()
                        else: app.window.ui.geometry('%dx%d' % target)
                        pump()
                        actual, parent = size(app.canvas), size(app.box)
                        for i, (dimension, minimum) in enumerate((('width', 'minWidth'), ('height', 'minHeight'))):
                            main = (axis == 'HBox') == (i == 0)
                            expected = (max(params[dimension], params.get(minimum, 0))
                                        if dimension in params and not (main and params.get('weight', 0) > 0)
                                        else parent[i])
                            self.assertAlmostEqual(actual[i], expected, delta=1)
