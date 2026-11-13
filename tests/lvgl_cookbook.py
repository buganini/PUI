"""Drive the LVGL cookbook headlessly with a simulated pointer.

    PYTHONPATH=. env/bin/python tests/lvgl_cookbook.py
"""
import os
import unittest

os.environ['PUI_BACKEND'] = 'lvgl'
os.environ['PUI_LVGL_DRIVER'] = 'headless#width=1024#height=768'

from PUI.cookbook.app import Cookbook, pages
from PUI.lvgl import Button, Checkbox, ComboBox, Label, RadioButton, Scroll, TextField, Tabs, Image
from PUI.lvgl.base import ffi, lib
from PUI.lvgl.testing import settle, find, tap_node, type_text, drag
from PUI.lvgl import Splitter, Grid


def texts(app):
    found = []
    stack = [app]
    while stack:
        node = stack.pop().get_node()
        if isinstance(node, Label) and node.ui is not None:
            found.append(node.text)
        stack.extend(node.children)
    return found


class LvglCookbook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Cookbook()
        cls.app.redraw()
        settle(cls.app)

    def open(self, page):
        menu = find(self.app, lambda n: isinstance(n, Label) and n.text == page and n._onClicked)
        self.assertIsNotNone(menu, page)
        tap_node(self.app, menu)
        self.assertEqual(self.app.state.page, page)
        return find(self.app, lambda n: getattr(n, '_id', None) == 'result')

    def button(self, root, text):
        node = find(root, lambda n: isinstance(n, Button) and n.text == text)
        self.assertIsNotNone(node, text)
        return node

    def test_every_page_mounts(self):
        for supported, name, _ in pages:
            if 'L' in supported:
                result = self.open(name)
                self.assertNotIn('Not Supported for this backend', texts(result), name)

    def test_button(self):
        result = self.open('Button')
        tap_node(self.app, self.button(result, 'B'))
        self.assertIn('B', texts(result.get_node()))
        tap_node(self.app, self.button(result.get_node(), 'Disabled'))
        self.assertIn('B', texts(result.get_node()))

    def test_checkbox(self):
        result = self.open('Checkbox')
        box = find(result, lambda n: isinstance(n, Checkbox) and n.text == 'checkbox 2')
        tap_node(self.app, box)
        self.assertIn('Model value 2: False', texts(result.get_node()))
        box = find(result.get_node(), lambda n: isinstance(n, Checkbox) and n.text == 'checkbox 4')
        tap_node(self.app, box)
        self.assertIn("List value: ['value 4']", texts(result.get_node()))
        disabled = find(result.get_node(), lambda n: isinstance(n, Checkbox) and n.text == 'Disabled (unchecked)')
        tap_node(self.app, disabled)
        self.assertFalse(lib.lv_obj_has_state(disabled.get_node().ui, lib.LV_STATE_CHECKED))

    def test_radio(self):
        result = self.open('RadioButton')
        for value in ('B', 'A', 'A'):
            radio = find(result.get_node(), lambda n: isinstance(n, RadioButton) and n.text == value)
            tap_node(self.app, radio)
            radios = [find(result.get_node(), lambda n, t=t: isinstance(n, RadioButton) and n.text == t) for t in 'AB']
            checked = [bool(lib.lv_obj_has_state(r.ui, lib.LV_STATE_CHECKED)) for r in radios]
            self.assertEqual(checked, [value == 'A', value == 'B'])

    def test_progress(self):
        result = self.open('ProgressBar')
        before = int(find(result, lambda n: isinstance(n, Label) and n.text.isdigit()).text)
        tap_node(self.app, self.button(result, '+5'))
        after = int(find(result.get_node(), lambda n: isinstance(n, Label) and n.text.isdigit()).text)
        self.assertEqual(after, before + 5)

    def test_textfield_commit(self):
        result = self.open('TextField')
        tap_node(self.app, self.button(result, 'Clear'))
        field = find(result.get_node(), lambda n: isinstance(n, TextField) and n.edit_model is not None)
        type_text(self.app, field, 'abc', commit=False)
        self.assertIn('Editing:abc', texts(result.get_node()))
        self.assertIn('State:', texts(result.get_node()))
        lib.lv_obj_send_event(field.get_node().ui, lib.LV_EVENT_READY, ffi.NULL)
        settle(self.app)
        self.assertIn('State:abc', texts(result.get_node()))

    def test_textfield_commit_on_click_elsewhere(self):
        result = self.open('TextField')
        tap_node(self.app, self.button(result, 'Clear'))
        field = find(result.get_node(), lambda n: isinstance(n, TextField) and n.edit_model is None)
        type_text(self.app, field, 'xyz', commit=False)
        tap_node(self.app, find(result.get_node(), lambda n: isinstance(n, Label) and n.text == 'State Model'))
        tap_node(self.app, self.button(result.get_node(), 'Set something'))
        self.assertIn('State:something', texts(result.get_node()))

    def test_tabs(self):
        result = self.open('Tab')
        tap_node(self.app, self.button(result, 'Tab 2'))
        tabs = find(result.get_node(), lambda n: isinstance(n, Tabs))
        self.assertEqual(tabs.model.value, 'Tab 2')

    def test_scroll_end(self):
        result = self.open('Scroll')
        scroll = find(result, lambda n: isinstance(n, Scroll))
        self.assertLessEqual(lib.lv_obj_get_scroll_bottom(scroll.ui), 1)
        tap_node(self.app, self.button(result, '+'))
        scroll = find(result.get_node(), lambda n: isinstance(n, Scroll))
        self.assertLessEqual(lib.lv_obj_get_scroll_bottom(scroll.ui), 1)
        self.assertIn('Row 101', texts(result.get_node()))

    def test_image(self):
        result = self.open('Image')
        image = find(result, lambda n: isinstance(n, Image))
        self.assertEqual(lib.lv_obj_get_width(image.ui), 400)
        self.assertGreater(lib.lv_obj_get_height(image.ui), 100)
        tap_node(self.app, image)
        self.assertIn('Clicked: 1', texts(result.get_node()))

    def test_combobox(self):
        result = self.open('Combobox')
        combo = find(result, lambda n: isinstance(n, ComboBox) and n.text_model is not None and not n.editable and not n.disabled)
        lib.lv_dropdown_set_selected(combo.ui, 1)
        lib.lv_obj_send_event(combo.ui, lib.LV_EVENT_VALUE_CHANGED, ffi.NULL)
        settle(self.app)
        self.assertIn('Text: Value 2', texts(result.get_node()))

    def test_splitter_drag(self):
        self.open('Button')
        splitter = find(self.app, lambda n: isinstance(n, Splitter) and n._id == 'example-panes')
        code = find(splitter, lambda n: getattr(n, '_id', None) == 'code')
        before = lib.lv_obj_get_width(code.ui)
        handle = splitter._native.store['handles'][0].obj
        area = ffi.new('lv_area_t *')
        lib.lv_obj_get_coords(handle, area)
        x, y = (area.x1 + area.x2) // 2, (area.y1 + area.y2) // 2
        drag(self.app, (x, y), (x - 100, y))
        self.assertAlmostEqual(lib.lv_obj_get_width(code.ui), before - 100, delta=2)

    def test_adaptive_grid_follows_splitter(self):
        self.open('Adaptive Grid')
        splitter = find(self.app, lambda n: isinstance(n, Splitter) and n._id == 'example-panes')
        handle = splitter._native.store['handles'][0].obj
        area = ffi.new('lv_area_t *')
        lib.lv_obj_get_coords(handle, area)
        x, y = (area.x1 + area.x2) // 2, (area.y1 + area.y2) // 2
        try:
            drag(self.app, (x, y), (x - 350, y))
            settle(self.app)
            grid = find(self.app, lambda n: isinstance(n, Grid))
            scroll = lib.lv_obj_get_parent(grid.ui)
            self.assertEqual(grid._grid_columns, 3)
            # The grid's tracks fill the scroll viewport, not only their content.
            self.assertGreaterEqual(lib.lv_obj_get_width(grid.ui), lib.lv_obj_get_content_width(scroll) - 1)
            tile = find(grid, lambda n: getattr(n, '_id', None) == 'A')
            self.assertGreater(lib.lv_obj_get_width(tile.ui), 200)
        finally:
            drag(self.app, (x - 350, y), (x, y))


if __name__ == '__main__':
    unittest.main()
