"""Named CSS/OpenType weights and backend style conversions."""
import asyncio
import unittest
from PUI import FontWeight, Anchor, Side
from PUI.common import font_weight


class FontWeightTests(unittest.TestCase):
    def test_named_values_and_aliases(self):
        self.assertEqual([int(w) for w in FontWeight], [100, 200, 300, 400, 500, 600, 700, 800, 900, 950])
        for alias, name in [('Hairline','Thin'), ('UltraLight','ExtraLight'),
                            ('Regular','Normal'), ('SemiBold','DemiBold'),
                            ('UltraBold','ExtraBold'), ('Heavy','Black'), ('UltraBlack','ExtraBlack')]:
            self.assertIs(getattr(FontWeight, alias), getattr(FontWeight, name))
        self.assertEqual(Anchor.LeftTop.value, ('left', 'top'))
        self.assertEqual(Side.Top.value, 'n')
        self.assertFalse(hasattr(Anchor, 'LEFT_TOP'))
        self.assertFalse(hasattr(Side, 'TOP'))
        self.assertEqual(font_weight(FontWeight.Bold), 700)
        self.assertIs(type(font_weight(FontWeight.Bold)), int)
        self.assertEqual(font_weight(550), 550)
        for invalid in (True, 0, 1001, 550.5, 'medium', 'bold', 'normal'):
            with self.assertRaises(ValueError):
                font_weight(invalid)

    def test_native_font_weight(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from PUI.PySide6 import Application, Window, Label
        from PUI.dom import recur_delete
        class Demo(Application):
            weight = FontWeight.Bold
            def content(self):
                with Window():
                    Label('Weight').style(fontWeight=self.weight)
        root = Demo();root.ui = app
        try:
            for weight, expected in ((FontWeight.Bold,700),(FontWeight.Light,300),(550,550),(None,400)):
                root.weight = weight;root.sync();app.processEvents()
                widget = root.children[0].children[0].ui
                widget.ensurePolished()
                self.assertEqual(int(widget.font().weight()), expected)
        finally:
            root.ui = None
            recur_delete(root,root,True)


class BrowserFontWeight(unittest.IsolatedAsyncioTestCase):
    async def test_named_weight_serializes_as_plain_integer(self):
        from PUI.web import Application, Window, Label
        from PUI.web.runtime import Runtime
        class Demo(Application):
            def content(self):
                with Window():
                    Label('Weight').style(fontWeight=FontWeight.SemiBold)
        runtime = Runtime(asyncio.get_running_loop())
        try:
            runtime.app=Demo();runtime.app.sync()
            style=runtime.snapshot()['roots'][0]['children'][0]['style']
            self.assertEqual(style['font_weight'], 600)
            self.assertIs(type(style['font_weight']),int)
        finally:
            runtime.close()
