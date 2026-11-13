"""Headless helpers: render an Application without a window and save PNGs.

Use driver="headless#width=W#height=H" for the Application.
"""
from __future__ import annotations
import struct
import zlib
from .base import ffi, lib, runtime


def settle(app, rounds=8):
    """Run queued redraws, timers and LVGL layout until things are quiet."""
    for _ in range(rounds):
        app.process_events()
    lib.lv_obj_update_layout(lib.lv_screen_active())


def _snapshot_argb(obj):
    lib.lv_obj_update_layout(obj)
    buf = lib.lv_snapshot_take(obj, lib.LV_COLOR_FORMAT_ARGB8888)
    if buf == ffi.NULL:
        raise RuntimeError('lv_snapshot_take failed')
    try:
        w, h = lib.lv_obj_get_width(obj), lib.lv_obj_get_height(obj)
        stride = buf.data_size // h
        raw = ffi.buffer(buf.data, buf.data_size)[:]
    finally:
        lib.lv_draw_buf_destroy(buf)
    return w, h, [raw[y * stride:y * stride + w * 4] for y in range(h)]


def snapshot_rgb(obj=None):
    """RGB rows of obj (default: the screen with the top layer composited)."""
    w, h, rows = _snapshot_argb(lib.lv_screen_active() if obj is None else obj)
    top = None
    if obj is None:
        layer = lib.lv_layer_top()
        if lib.lv_obj_get_child_count(layer):
            top = _snapshot_argb(layer)[2]
    result = []
    for y, row in enumerate(rows):
        rgb = bytearray(w * 3)
        rgb[0::3] = row[2::4]
        rgb[1::3] = row[1::4]
        rgb[2::3] = row[0::4]
        if top is not None:
            over = top[y]
            for x in range(w):
                a = over[x * 4 + 3]
                if a:
                    for c, src in ((0, 2), (1, 1), (2, 0)):
                        rgb[x * 3 + c] = (over[x * 4 + src] * a + rgb[x * 3 + c] * (255 - a)) // 255
        result.append(bytes(rgb))
    return w, h, result


def save_png(path, obj=None):
    w, h, rows = snapshot_rgb(obj)
    raw = b''.join(b'\x00' + row for row in rows)

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(raw, 6)))
        f.write(chunk(b'IEND', b''))


def find(node, predicate):
    """Depth-first search of the mounted node tree."""
    stack = [node]
    while stack:
        current = stack.pop()
        current = current.get_node()
        if predicate(current):
            return current
        stack.extend(reversed(list(current.children)))
    return None


def click(node):
    """Deliver a native click to a node's LVGL object."""
    node = node.get_node()
    lib.lv_obj_send_event(node.ui, lib.LV_EVENT_CLICKED, ffi.NULL)


# ---- Simulated pointer: exercises LVGL's real hit testing and click logic ----

_pointer = {'indev': None, 'x': 0, 'y': 0, 'pressed': False}


@ffi.def_extern()
def _pui_test_pointer_cb(indev, data):
    data.point.x = _pointer['x']
    data.point.y = _pointer['y']
    data.state = lib.LV_INDEV_STATE_PRESSED if _pointer['pressed'] else lib.LV_INDEV_STATE_RELEASED


def _indev():
    if _pointer['indev'] is None:
        indev = lib.lv_indev_create()
        lib.lv_indev_set_type(indev, lib.LV_INDEV_TYPE_POINTER)
        lib.lv_indev_set_read_cb(indev, lib._pui_test_pointer_cb)
        _pointer['indev'] = indev
    return _pointer['indev']


def center(node):
    area = ffi.new('lv_area_t *')
    lib.lv_obj_get_coords(node.get_node().ui, area)
    return (area.x1 + area.x2) // 2, (area.y1 + area.y2) // 2


def tap(x, y):
    indev = _indev()
    _pointer.update(x=x, y=y, pressed=True)
    lib.lv_indev_read(indev)
    _pointer['pressed'] = False
    lib.lv_indev_read(indev)


def tap_node(app, node):
    lib.lv_obj_update_layout(lib.lv_screen_active())
    lib.lv_obj_scroll_to_view_recursive(node.get_node().ui, lib.LV_ANIM_OFF)
    lib.lv_obj_update_layout(lib.lv_screen_active())
    tap(*center(node))
    settle(app)


def type_text(app, node, text, commit=True):
    """Type into a focused TextField/TextEdit, optionally committing (Enter/blur)."""
    obj = node.get_node().ui
    tap_node(app, node)
    lib.lv_textarea_add_text(obj, text.encode('utf-8'))
    settle(app)
    if commit:
        lib.lv_obj_send_event(obj, lib.LV_EVENT_READY, ffi.NULL)
        settle(app)


def drag(app, start, end, steps=5):
    indev = _indev()
    _pointer.update(x=start[0], y=start[1], pressed=True)
    lib.lv_indev_read(indev)
    for i in range(1, steps + 1):
        _pointer['x'] = start[0] + (end[0] - start[0]) * i // steps
        _pointer['y'] = start[1] + (end[1] - start[1]) * i // steps
        lib.lv_indev_read(indev)
    _pointer['pressed'] = False
    lib.lv_indev_read(indev)
    settle(app)


def hover(app, x, y):
    """Move the simulated pointer without pressing."""
    indev = _indev()
    _pointer.update(x=x, y=y, pressed=False)
    lib.lv_indev_read(indev)
    settle(app)
