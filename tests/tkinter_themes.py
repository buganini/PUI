"""Theme coverage for every implemented widget family; requires a Tk display."""
import unittest
from tkinter import ttk
import PUI.tkinter as UI
from PUI.dom import recur_delete


class ThemeTests(unittest.TestCase):
    def test_widget_families_across_installed_themes(self):
        nodes = {}
        def remember(name, node):
            nodes[name] = node
            return node
        def paint(canvas):
            canvas.drawText(0, 0, 'default')
            canvas.drawText(0, 20, 'explicit', color=0x123456)
        class Example(UI.Application):
            def content(self):
                with remember('window', UI.Window(size=(640, 600))):
                    with remember('vbox', UI.VBox()):
                        with remember('hbox', UI.HBox()):
                            remember('label', UI.Label('label'))
                            remember('text', UI.Text('text'))
                            remember('button', UI.Button('button'))
                            remember('spacer', UI.Spacer())
                        remember('check', UI.Checkbox('check', UI.DummyBinding(True)))
                        remember('radio', UI.RadioButton('radio', 'a', UI.DummyBinding('a')))
                        remember('entry', UI.TextField(UI.DummyBinding('entry')))
                        remember('masked', UI.MaskedField(UI.DummyBinding('secret')))
                        with remember('combo', UI.ComboBox().style(bgColor=0x345678)):
                            UI.ComboBoxItem('one', 1)
                        remember('progress', UI.ProgressBar(0.5))
                        remember('divider', UI.Divider())
                        with remember('grid', UI.Grid()):
                            UI.Label('cell').grid(row=0, column=0)
                        with remember('scroll', UI.Scroll().style(bgColor=0x234567)):
                            UI.Label('scroll')
                        with remember('tabs', UI.Tabs()):
                            with remember('tab', UI.Tab('page')):
                                UI.Label('tab')
                        with remember('views', UI.Views(UI.DummyBinding('page'))):
                            UI.Label('view').id('page')
                        remember('table', UI.Table().style(bgColor=0x456789))
                        remember('canvas', UI.Canvas(paint).layout(width=120, height=50))
        root = Example()
        self.addCleanup(lambda: recur_delete(root, root, True))
        root.sync()
        errors = []
        root.ui.report_callback_exception = lambda *args: errors.append(args)
        style = ttk.Style(root.ui)
        for theme in style.theme_names():
            with self.subTest(theme=theme):
                style.theme_use(theme)
                root.sync()
                root.ui.update()
                for name, node in nodes.items():
                    if node.ttk_style:
                        self.assertIsInstance(node.ui, ttk.Widget, name)
                        self.assertTrue(style.layout(node.ui.cget('style')), name)
                for name in ('label', 'text'):
                    self.assertEqual(str(nodes[name].ui.cget('background')),
                                     style.lookup('TLabel', 'background'))
                self.assertEqual(str(nodes['window'].ui.cget('background')),
                                 style.lookup('TFrame', 'background'))
                canvas = nodes['canvas'].ui
                self.assertEqual(str(canvas.cget('background')), style.lookup('TFrame', 'background'))
                self.assertEqual(canvas.itemcget(canvas.find_all()[0], 'fill'),
                                 style.lookup('TLabel', 'foreground') or 'black')
                self.assertEqual(canvas.itemcget(canvas.find_all()[1], 'fill'), '#123456')
                self.assertEqual(int(canvas.cget('highlightthickness')), 0)
                combo_style = nodes['combo'].ui.cget('style')
                self.assertEqual(style.lookup(combo_style, 'fieldbackground'), '#345678')
                table_style = nodes['table'].ui.cget('style')
                self.assertEqual(style.lookup(table_style, 'background'), '#456789')
                self.assertEqual(style.lookup(table_style, 'fieldbackground'), '#456789')
                scroll = nodes['scroll'].ui
                self.assertEqual(str(scroll.canvas.cget('background')), '#234567')
                self.assertEqual(style.lookup(scroll.container.cget('style'), 'background'), '#234567')
        self.assertEqual(errors, [])
