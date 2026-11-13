"""Render every LVGL cookbook page headlessly into PNGs.

    PUI_BACKEND=lvgl env/bin/python tests/lvgl/cookbook_snapshots.py OUTDIR [page ...]
"""
import os
import sys
os.environ['PUI_BACKEND'] = 'lvgl'
os.environ.setdefault('PUI_LVGL_DRIVER', 'headless#width=1024#height=768')
from PUI.cookbook.app import Cookbook, pages, flags
from PUI.lvgl.testing import settle, save_png

out = sys.argv[1]
wanted = sys.argv[2:]
os.makedirs(out, exist_ok=True)
app = Cookbook()
app.redraw()
settle(app)
for supported, name, _ in pages:
    if 'L' not in supported or (wanted and name not in wanted):
        continue
    app.state.page = name
    settle(app)
    path = os.path.join(out, name.replace(' ', '_').replace('&', 'and').replace('(', '').replace(')', '') + '.png')
    save_png(path)
    print('saved', path)
