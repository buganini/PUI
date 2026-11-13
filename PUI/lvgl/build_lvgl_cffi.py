"""CFFI build script for pui_lvgl.

Usage:
    python PUI/lvgl/build_lvgl_cffi.py

This compiles the C wrapper and links LVGL + the chosen display driver
into a Python extension module ``PUI.lvgl._lib``.

Environment variables:
    LVGL_PATH       - path to LVGL source tree (default: /usr/local/src/lvgl)
    PUI_DRV         - space-separated driver list (default: "sdl2")
                      Recognised tokens: sdl2, x11, spi
"""

import os
import cffi

ffi = cffi.FFI()

# ---- cdef: the C declarations visible to Python ----

ffi.cdef("""
/* Init / deinit */
int  pui_lvgl_init(const char *driver_config);
void pui_lvgl_deinit(void);
uint32_t pui_lvgl_timer_handler(void);
int  pui_lvgl_is_running(void);

/* Screen */
void *pui_lvgl_screen_active(void);

/* Object lifecycle */
void *pui_lv_obj_create(void *parent);
void  pui_lv_obj_delete(void *obj);
void  pui_lv_obj_clean(void *obj);

/* Label */
void *pui_lv_label_create(void *parent);
void  pui_lv_label_set_text(void *obj, const char *text);

/* Button */
void *pui_lv_btn_create(void *parent);
void *pui_lv_btn_get_or_create_label(void *btn);

/* Checkbox */
void *pui_lv_checkbox_create(void *parent);
void  pui_lv_checkbox_set_text(void *obj, const char *text);
void  pui_lv_checkbox_set_checked(void *obj, int checked);
int   pui_lv_checkbox_is_checked(void *obj);

/* Image */
void *pui_lv_image_create(void *parent);
void  pui_lv_image_set_src_file(void *obj, const char *path);

/* ProgressBar */
void *pui_lv_bar_create(void *parent);
void  pui_lv_bar_set_value(void *obj, int value);
void  pui_lv_bar_set_range(void *obj, int min, int max);

/* TextField */
void *pui_lv_textarea_create(void *parent);
void  pui_lv_textarea_set_text(void *obj, const char *text);
const char *pui_lv_textarea_get_text(void *obj);
void  pui_lv_textarea_set_one_line(void *obj, int one_line);
void  pui_lv_textarea_set_placeholder(void *obj, const char *text);

/* Scroll */
void *pui_lv_scroll_create(void *parent);

/* Size / position */
void pui_lv_obj_set_width(void *obj, int w);
void pui_lv_obj_set_height(void *obj, int h);
void pui_lv_obj_set_size(void *obj, int w, int h);
void pui_lv_obj_set_size_content(void *obj);
void pui_lv_obj_set_width_pct(void *obj, int pct);
void pui_lv_obj_set_height_pct(void *obj, int pct);
void pui_lv_obj_set_min_width(void *obj, int w);
void pui_lv_obj_set_min_height(void *obj, int h);
int  pui_lv_obj_get_width(void *obj);
int  pui_lv_obj_get_height(void *obj);
int  pui_lv_obj_get_content_width(void *obj);
int  pui_lv_obj_get_content_height(void *obj);

/* Flex layout */
#define PUI_FLEX_FLOW_ROW            0
#define PUI_FLEX_FLOW_COLUMN         1
#define PUI_FLEX_FLOW_ROW_REVERSE    2
#define PUI_FLEX_FLOW_COLUMN_REVERSE 3

#define PUI_FLEX_ALIGN_START   0
#define PUI_FLEX_ALIGN_CENTER  1
#define PUI_FLEX_ALIGN_END     2

void pui_lv_obj_set_flex_flow(void *obj, int flow);
void pui_lv_obj_set_flex_grow(void *obj, int grow);
void pui_lv_obj_set_flex_align(void *obj, int main_place, int cross_place, int track_place);

/* Grid layout */
void pui_lv_obj_set_grid(void *obj, int cols, int rows);
void pui_lv_obj_set_grid_cell(void *obj, int col, int row, int colspan, int rowspan);

/* Style */
void pui_lv_obj_set_style_bg_color(void *obj, uint32_t color);
void pui_lv_obj_set_style_bg_opa(void *obj, int opa);
void pui_lv_obj_set_style_text_color(void *obj, uint32_t color);
void pui_lv_obj_set_style_text_font_size(void *obj, int size);
void pui_lv_obj_set_style_pad_all(void *obj, int pad);
void pui_lv_obj_set_style_pad(void *obj, int top, int right, int bottom, int left);
void pui_lv_obj_set_style_pad_row(void *obj, int pad);
void pui_lv_obj_set_style_pad_column(void *obj, int pad);
void pui_lv_obj_set_style_border_width(void *obj, int w);
void pui_lv_obj_set_style_radius(void *obj, int r);
void pui_lv_obj_set_style_margin(void *obj, int top, int right, int bottom, int left);
void pui_lv_obj_set_transparent(void *obj);

/* Visibility / state */
void pui_lv_obj_set_hidden(void *obj, int hidden);
void pui_lv_obj_set_clickable(void *obj, int clickable);
void pui_lv_obj_set_scrollable(void *obj, int scrollable);
void pui_lv_obj_set_disabled(void *obj, int disabled);

/* Child ordering */
void pui_lv_obj_move_to_index(void *obj, int index);
void pui_lv_obj_center(void *obj);

/* Events */
#define PUI_EVENT_CLICKED      1
#define PUI_EVENT_VALUE_CHANGED 2
#define PUI_EVENT_READY        3
#define PUI_EVENT_DELETE        100

extern "Python" void _pui_event_cb(int event_code, void *user_data);
void *pui_lv_obj_add_event_cb(void *obj, void (*cb)(int, void *), void *user_data);
void  pui_lv_obj_remove_event_cb(void *obj, void *descriptor);

/* Timer */
extern "Python" void _pui_timer_cb(void *user_data);
void *pui_lv_timer_create(void (*cb)(void *), int period_ms, void *user_data);
void  pui_lv_timer_delete(void *timer);

/* Helpers */
const char *pui_parse_driver_name(const char *config);
""")

# ---- set_source: point at our C wrapper ----

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
csrc_dir = os.path.join(project_root, "csrc")
lvgl_path = os.environ.get("LVGL_PATH", os.path.join(project_root, "lvgl-9.6.0"))
drivers = os.environ.get("PUI_DRV", "sdl2").split()

lv_conf_path = os.path.join(csrc_dir, "lv_conf.h")

build_dir = os.environ.get("PUI_LVGL_BUILD_DIR", os.path.join(project_root, "build-lvgl"))

define_macros = [
    ("LV_CONF_PATH", f'"{lv_conf_path}"'),
]
sources = [
    os.path.join(csrc_dir, "pui_lvgl.c"),
]
libraries = ["lvgl"]
include_dirs = [csrc_dir, lvgl_path]
library_dirs = [os.path.join(build_dir, "lvgl")]
extra_link_args = []

import subprocess

for drv in drivers:
    drv = drv.lower()
    define_macros.append(("PUI_DRV_" + drv.upper(), "1"))
    src = os.path.join(csrc_dir, f"driver_{drv}.c")
    if os.path.exists(src):
        sources.append(src)

    if drv == "sdl2":
        try:
            sdl2_cflags = subprocess.check_output(["pkg-config", "--cflags", "sdl2"], text=True).split()
            sdl2_libs = subprocess.check_output(["pkg-config", "--libs", "sdl2"], text=True).split()
            extra_link_args.extend(sdl2_libs)
        except (subprocess.CalledProcessError, FileNotFoundError):
            libraries.append("SDL2")
    elif drv == "x11":
        libraries.append("X11")

ffi.set_source(
    "PUI.lvgl.liblvgl",
    '#include "pui_lvgl.h"',
    sources=sources,
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    define_macros=define_macros,
    extra_link_args=extra_link_args,
)

if __name__ == "__main__":
    ffi.compile(verbose=True)
