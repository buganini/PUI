"""Drive the LVGL cookbook headlessly with a simulated pointer.

    PYTHONPATH=. env/bin/python tests/lvgl_cookbook.py
"""
import os
import time
import unittest

os.environ['PUI_BACKEND'] = 'lvgl'
os.environ['PUI_LVGL_DRIVER'] = 'headless#width=1024#height=768'

from PUI.cookbook.app import Cookbook, pages
from PUI.lvgl import Button, Checkbox, ComboBox, Label, RadioButton, Scroll, TextField, Tabs, Image
from PUI.lvgl.base import ffi, lib
from PUI.lvgl.testing import settle, find, tap_node, type_text, drag
from PUI.lvgl import Splitter, Grid, Canvas, Table, Tree, MenuBar
from PUI.lvgl.base import runtime
from PUI.lvgl.testing import hover, tap, center


def obj_center(obj):
    area = ffi.new('lv_area_t *')
    lib.lv_obj_get_coords(obj, area)
    return (area.x1 + area.x2) // 2, (area.y1 + area.y2) // 2


def top_buttons():
    probe = lib.lv_button_create(lib.lv_screen_active())
    button_class = lib.lv_obj_get_class(probe)
    lib.lv_obj_delete(probe)
    probe = lib.lv_label_create(lib.lv_screen_active())
    label_class = lib.lv_obj_get_class(probe)
    lib.lv_obj_delete(probe)
    found = {}

    def walk(obj):
        for i in range(lib.lv_obj_get_child_count(obj)):
            child = lib.lv_obj_get_child(obj, i)
            walk(child)
            if lib.lv_obj_get_class(child) == button_class and lib.lv_obj_get_child_count(child) == 1:
                label = lib.lv_obj_get_child(child, 0)
                if lib.lv_obj_get_class(label) == label_class:
                    found[ffi.string(lib.lv_label_get_text(label)).decode()] = child
    walk(lib.lv_layer_top())
    return found


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

    def test_canvas_hover_and_wheel(self):
        self.open('HeavyCanvas')
        canvas = find(self.app, lambda n: isinstance(n, Canvas))
        x, y = center(canvas)
        hover(self.app, x, y)
        hover(self.app, x + 4, y)
        view = find(self.app, lambda n: type(n).__name__ == 'HeavyCanvasExample')
        self.assertIsNotNone(view.state.cursor)
        before = view.state.viewport
        diff = ffi.new('int32_t *', -1)
        lib.lv_obj_send_event(find(self.app, lambda n: isinstance(n, Canvas)).ui, lib.LV_EVENT_ROTARY, diff)
        settle(self.app)
        self.assertNotEqual(find(self.app, lambda n: type(n).__name__ == 'HeavyCanvasExample').state.viewport, before)
        hover(self.app, 2, 2)
        self.assertIsNone(find(self.app, lambda n: type(n).__name__ == 'HeavyCanvasExample').state.cursor)

    def test_table_edit(self):
        result = self.open('Table')
        table = find(result, lambda n: isinstance(n, Table))
        lib.lv_table_set_selected_cell(table.ui, 2, 1)  # B1 (header row/column first)
        lib.lv_obj_send_event(table.ui, lib.LV_EVENT_DOUBLE_CLICKED, ffi.NULL)
        settle(self.app)
        editor = find(self.app, lambda n: isinstance(n, Table)).editor
        self.assertIsNotNone(editor)
        lib.lv_textarea_set_text(editor.field, b'edited')
        tap(*obj_center(top_buttons()['Save']))
        settle(self.app)
        self.assertIn('B1: edited', texts(result.get_node()))
        self.assertIsNone(find(self.app, lambda n: isinstance(n, Table)).editor)

    def test_table_edit_with_pointer(self):
        """A real double click: lv_table clears its selection on release."""
        result = self.open('Table')
        table = find(result, lambda n: isinstance(n, Table))
        area = ffi.new('lv_area_t *')
        lib.lv_obj_get_coords(table.ui, area)
        # Rows are one text line plus the cell padding (4 + 4); header row first.
        inset = (lib.lv_obj_get_height(table.ui) - lib.lv_obj_get_content_height(table.ui)) // 2
        row_height = lib.lv_obj_get_style_text_font(table.ui, lib.LV_PART_ITEMS).line_height + 8
        x = area.x1 + inset + 60 + 40  # column 1, after the row header column
        y = area.y1 + inset + row_height * 2 + row_height // 2  # data row 2: B1
        tap(x, y)
        settle(self.app)
        table = find(self.app, lambda n: isinstance(n, Table))
        self.assertEqual(table._native.store.get('cell'), (2, 1))
        self.assertIsNone(table.editor)
        time.sleep(0.6)  # the next two clicks must not pair with this one
        from PUI.lvgl.testing import _indev, _pointer
        for _ in range(2):  # double click on the same spot
            _pointer.update(x=x, y=y, pressed=True)
            lib.lv_indev_read(_indev())
            _pointer['pressed'] = False
            lib.lv_indev_read(_indev())
        settle(self.app)
        editor = find(self.app, lambda n: isinstance(n, Table)).editor
        self.assertIsNotNone(editor)
        lib.lv_textarea_set_text(editor.field, b'typed')
        tap(*obj_center(top_buttons()['Save']))
        settle(self.app)
        self.assertIn('B1: typed', texts(result.get_node()))

    def test_tree_toggle(self):
        self.open('Tree')
        tree = find(self.app, lambda n: isinstance(n, Tree))
        expanded = len(tree._native.store['visible'])
        _, arrow, _ = tree._native.store['rows'][0]
        tap(*obj_center(arrow))
        settle(self.app)
        self.assertEqual(len(find(self.app, lambda n: isinstance(n, Tree))._native.store['visible']), 1)
        tap(*obj_center(arrow))
        settle(self.app)
        self.assertEqual(len(find(self.app, lambda n: isinstance(n, Tree))._native.store['visible']), expanded)

    def test_modal(self):
        result = self.open('Modal')
        tap_node(self.app, self.button(result, 'Open Modal'))
        self.assertIn('State: True', texts(result.get_node()))
        close = find(self.app, lambda n: isinstance(n, Button) and n.text == 'Close Modal')
        tap_node(self.app, close)
        self.assertIn('State: False', texts(result.get_node()))

    def test_menu(self):
        from PUI.lvgl.menu import _popups
        bar = find(self.app, lambda n: isinstance(n, MenuBar))
        tap(*obj_center(bar._native.store['buttons'][0]))
        settle(self.app)
        self.assertEqual(len(_popups.levels), 1)
        tap(2, 760)  # outside closes
        settle(self.app)
        self.assertEqual(len(_popups.levels), 0)

    def test_confirm_and_prompt(self):
        result = self.open('Imperative')

        def answer(caption):
            def act():
                tap(*obj_center(top_buttons()[caption]))
            runtime.post_timer(0.05, act)
        answer('Yes')
        tap_node(self.app, self.button(result, 'Confirm'))
        self.assertIn('Confirm: True', texts(result.get_node()))
        answer('OK')
        tap_node(self.app, self.button(result.get_node(), 'Prompt'))
        self.assertIn('Prompt: default', texts(result.get_node()))

    def test_editable_combobox(self):
        from PUI.lvgl.combobox import _popup
        result = self.open('Combobox')
        combo = find(result, lambda n: isinstance(n, ComboBox) and n.edit_model is not None)
        lib.lv_textarea_add_text(combo._native.store['field'], b'tok')
        settle(self.app)
        self.assertEqual(lib.lv_obj_get_child_count(_popup.panel), 2)
        tap(*obj_center(lib.lv_obj_get_child(_popup.panel, 0)))
        settle(self.app)
        self.assertIn('Autocomplete value: HND', texts(result.get_node()))


if __name__ == '__main__':
    unittest.main()
