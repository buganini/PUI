"""Font-family choices and native retained selection."""
import importlib
import unittest
from PUI.fontcombobox import font_choices
from PUI.dom import recur_delete


class FontChoicesTests(unittest.TestCase):
    def test_choices(self):
        self.assertEqual(font_choices(['Alpha', 'Beta', 'Alpha']), ('Alpha', 'Beta'))
        self.assertEqual(font_choices([]), ())
        with self.assertRaises(TypeError): font_choices('Arial')
        for values in ([None], [''], ['  ']):
            with self.assertRaises(ValueError): font_choices(values)


class NativeFontTests(unittest.TestCase):
    def exercise(self, backend):
        ui = importlib.import_module('PUI.' + backend)
        class App(ui.Application):
            disabled = False
            fonts = ('Alpha', 'Beta')
            def setup(self):
                self.state = ui.State({'font': 'Alpha'})
            def content(self):
                with ui.Window():
                    self.picker = ui.FontComboBox(self.state('font'), fonts=self.fonts, disabled=self.disabled)
        app = App()
        try:
            app.sync()
            widget = app.picker.ui
            if backend == 'PySide6':
                self.assertEqual(widget.currentText(), 'Alpha')
                widget.activated.emit(1)
            elif backend == 'wx':
                import wx
                self.assertEqual(widget.GetValue(), 'Alpha')
                widget.SetSelection(1)
                event = wx.CommandEvent(wx.EVT_COMBOBOX.typeId, widget.GetId())
                event.SetEventObject(widget)
                widget.GetEventHandler().ProcessEvent(event)
            else:
                self.assertEqual(widget.get(), 'Alpha')
                widget.current(1)
                widget.event_generate('<<ComboboxSelected>>')
            self.assertEqual(app.state['font'], 'Beta')
            app.disabled = True
            app.sync()
            self.assertIs(app.picker.ui, widget)
            app.state['font'] = 'Alpha'
            app.sync()
            if backend == 'PySide6':
                self.assertFalse(widget.isEnabled())
                self.assertEqual(widget.currentText(), 'Alpha')
            elif backend == 'wx':
                self.assertFalse(widget.IsEnabled())
                self.assertEqual(widget.GetValue(), 'Alpha')
            else:
                self.assertIn('disabled', widget.state())
                self.assertEqual(widget.get(), 'Alpha')
            app.disabled = False
            app.fonts = None
            app.sync()
            if backend == 'PySide6':
                from PySide6.QtWidgets import QFontComboBox
                self.assertIsInstance(app.picker.ui, QFontComboBox)
                self.assertGreater(app.picker.ui.count(), 0)
            else:
                self.assertGreater(len(app.picker.children), 0)
            self.assertEqual(app.state['font'], 'Alpha')  # Enumerating never overwrites State.
        finally:
            recur_delete(app, app, True)

    def test_qt(self): self.exercise('PySide6')
    def test_wx(self): self.exercise('wx')
    def test_tk(self): self.exercise('tkinter')
