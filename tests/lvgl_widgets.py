"""LVGL widget behaviour that the cookbook pages do not reach.

    PYTHONPATH=. env/bin/python tests/lvgl_widgets.py

One headless application; each test picks what it shows through state.page.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ['PUI_BACKEND'] = 'lvgl'
os.environ['PUI_LVGL_DRIVER'] = 'headless#width=800#height=600'

from PUI.state import State
from PUI.lvgl import (Application, Window, VBox, HBox, Grid, Label, Splitter, Divider, Image,
                      ComboBox, ComboBoxItem, Spacer)
from PUI.lvgl.base import ffi, lib
from PUI.lvgl.testing import settle, find, drag, tap

ROOT = Path(__file__).resolve().parents[1]
STAR = str(ROOT / 'PUI' / 'cookbook' / 'assets' / 'star.png')


def coords(obj):
    area = ffi.new('lv_area_t *')
    lib.lv_obj_get_coords(obj, area)
    return area


def by_id(app, name):
    return find(app, lambda n: getattr(n, '_id', None) == name)


class App(Application):
    def setup(self):
        self.state = State()
        self.state.page = None
        self.state.image = STAR
        self.state.nested = 'nested and rather wide text'

    def content(self):
        page = self.state.page
        with Window(title='Widgets', size=(800, 600)):
            with VBox().layout(weight=1):
                if page == 'grid':
                    # A fixed size: a child's change does not resize the grid itself.
                    with Grid().layout(width=700, height=60).id('fixed'):
                        Label('a').layout(width=50).grid(row=0, column=0).id('cell')
                        Label('b').grid(row=0, column=1).id('after')
                    with HBox():  # the grid takes its content width
                        with Grid().id('outer'):
                            with Grid().grid(row=0, column=0).id('inner'):
                                Label(self.state.nested).grid(row=0, column=0)
                            Label('b').grid(row=0, column=1).id('next')
                        Spacer()
                elif page == 'splitter':
                    with Splitter().layout(width=400, height=200).id('split'):
                        with VBox().layout(margin=10).id('left'):
                            Label('left')
                        with VBox().id('right'):
                            Label('right')
                elif page == 'divider':
                    with VBox():
                        Divider().id('in-box')
                    with Grid():
                        Divider().grid(row=0, column=0).id('in-grid')
                        Label('x' * 20).grid(row=0, column=1)
                elif page == 'image':
                    Image(self.state.image).id('image')
                elif page == 'combobox':
                    with ComboBox(editable=True).id('empty-editable'):
                        pass
                    with ComboBox().id('empty'):
                        pass
                    with ComboBox().id('filled'):
                        ComboBoxItem('one')


class LvglWidgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App()
        cls.app.redraw()
        settle(cls.app)

    def reported(self, action):
        """PUI prints update() errors instead of raising them; return that output."""
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            action()
            settle(self.app)
        return out.getvalue()

    def show(self, page):
        self.app.state.page = page
        settle(self.app)

    def test_grid_follows_native_child_changes(self):
        self.show('grid')
        cell = by_id(self.app, 'cell')
        after = by_id(self.app, 'after')
        before = coords(after.ui).x1
        # Resized natively (no PUI sync): the column must still widen.
        lib.lv_obj_set_width(cell.ui, 500)
        settle(self.app)
        settle(self.app)  # settle's closing layout pass queues the re-measure
        self.assertGreater(coords(after.ui).x1, before + 200)

    def test_nested_grid_shrinks_with_its_content(self):
        self.show('grid')
        wide = coords(by_id(self.app, 'next').ui).x1
        # The stretched nested grid must report what its label needs, not the
        # cell it was given, so the outer column can shrink again.
        self.app.state.nested = 'short'
        settle(self.app)
        settle(self.app)
        try:
            self.assertLess(coords(by_id(self.app, 'next').ui).x1, wide - 100)
        finally:
            self.app.state.nested = 'nested and rather wide text'
            settle(self.app)

    def test_splitter_applies_pane_margins(self):
        self.show('splitter')
        split, left = by_id(self.app, 'split'), by_id(self.app, 'left')
        outer, pane = coords(split.ui), coords(left.ui)
        self.assertEqual(pane.x1 - outer.x1, 10)
        self.assertEqual(pane.y1 - outer.y1, 10)
        self.assertEqual(outer.y2 - pane.y2, 10)

    def test_splitter_keeps_every_pane_visible(self):
        self.show('splitter')
        split = by_id(self.app, 'split')
        right = by_id(self.app, 'right')
        handle = coords(split._native.store['handles'][0].obj)
        x, y = (handle.x1 + handle.x2) // 2, (handle.y1 + handle.y2) // 2
        drag(self.app, (x, y), (x + 1000, y))
        settle(self.app)
        self.assertGreaterEqual(lib.lv_obj_get_width(right.ui), 1)
        drag(self.app, (x + 1000, y), (x - 1000, y))
        settle(self.app)
        left = by_id(self.app, 'left')
        self.assertGreaterEqual(coords(split._native.store['handles'][0].obj).x1 - coords(split.ui).x1, 1)
        self.assertGreaterEqual(lib.lv_obj_get_width(left.ui), 0)

    def test_divider_is_drawn_only_in_boxes(self):
        self.show('divider')
        self.assertEqual(lib.lv_obj_get_style_bg_opa(by_id(self.app, 'in-box').ui, 0), lib.LV_OPA_COVER)
        self.assertEqual(lib.lv_obj_get_style_bg_opa(by_id(self.app, 'in-grid').ui, 0), lib.LV_OPA_TRANSP)

    def test_image_replaced_at_the_same_path(self):
        import shutil
        import struct
        import zlib
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'image.png')
            shutil.copy(STAR, path)
            self.app.state.image = path
            self.show('image')
            image = by_id(self.app, 'image')
            self.assertGreater(lib.lv_image_get_src_width(image.ui), 2)

            def png(width, height):
                raw = b''.join(b'\0' + b'\xff\0\0' * width for _ in range(height))

                def chunk(kind, data):
                    return (struct.pack('>I', len(data)) + kind + data
                            + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff))
                return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                        + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))
            Path(path).write_bytes(png(2, 3))
            os.utime(path, ns=(1, 1))
            self.app.redraw()
            settle(self.app)
            image = by_id(self.app, 'image')
            self.assertEqual((lib.lv_image_get_src_width(image.ui), lib.lv_image_get_src_height(image.ui)), (2, 3))

            Path(path).write_bytes(b'not an image')
            os.utime(path, ns=(2, 2))
            self.assertIn('Cannot decode image', self.reported(self.app.redraw))
        self.app.state.image = STAR
        self.app.state.page = None
        settle(self.app)

    def test_missing_image_raises(self):
        self.app.state.image = '/nonexistent/image.png'
        try:
            self.assertIn('FileNotFoundError', self.reported(lambda: self.show('image')))
        finally:
            self.app.state.image = STAR
            self.app.state.page = None
            settle(self.app)

    def test_combobox_without_items_is_disabled(self):
        self.show('combobox')
        self.assertTrue(lib.lv_obj_has_state(by_id(self.app, 'empty').ui, lib.LV_STATE_DISABLED))
        self.assertFalse(lib.lv_obj_has_state(by_id(self.app, 'filled').ui, lib.LV_STATE_DISABLED))
        store = by_id(self.app, 'empty-editable')._native.store
        self.assertTrue(lib.lv_obj_has_state(store['button'], lib.LV_STATE_DISABLED))
        self.assertFalse(lib.lv_obj_has_state(store['field'], lib.LV_STATE_DISABLED))


if __name__ == '__main__':
    unittest.main()
