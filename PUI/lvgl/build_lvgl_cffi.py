"""CFFI build script for pui_lvgl.

Usage:
    python PUI/lvgl/build_lvgl_cffi.py

This compiles the driver bring-up C code and links LVGL into a Python
extension module named after its drivers, e.g. ``PUI.lvgl.liblvgl_sdl2`` or
``PUI.lvgl.liblvgl_x11``, so builds for different drivers can coexist.
``PUI/lvgl/native.py`` picks one at import time.

Environment variables:
    LVGL_PATH          - path to the LVGL source tree (default: ./lvgl-9.6.0)
    PUI_DRV            - space-separated driver list (default: "sdl2")
                         Recognised tokens: sdl2, x11, spi
    PUI_LVGL_BUILD_DIR - CMake build of LVGL for these drivers
                         (default: ./build-lvgl-<drivers>)
"""

import os
import cffi

ffi = cffi.FFI()

# ---- cdef: the C declarations visible to Python ----

ffi.cdef("""
/* ==== PUI display/driver bring-up (csrc/pui_lvgl.c) ==== */
int  pui_lvgl_init(const char *driver_config);
void pui_lvgl_deinit(void);
uint32_t pui_lvgl_timer_handler(void);
int  pui_lvgl_is_running(void);
void pui_lvgl_set_title(const char *title);
void pui_lvgl_set_size(int w, int h);
const char *pui_parse_driver_name(const char *config);

/* ==== LVGL API, declared directly ==== */
typedef struct _lv_obj_t lv_obj_t;
typedef struct { int32_t x1; int32_t y1; int32_t x2; int32_t y2; } lv_area_t;
typedef struct _lv_event_t lv_event_t;
typedef struct _lv_event_dsc_t lv_event_dsc_t;
typedef struct _lv_display_t lv_display_t;
typedef struct _lv_group_t lv_group_t;
typedef struct _lv_indev_t lv_indev_t;
typedef struct { int32_t x; int32_t y; } lv_point_t;
typedef int... lv_indev_type_t;
typedef int... lv_indev_state_t;
typedef struct { lv_point_t point; uint32_t key; lv_indev_state_t state; ...; } lv_indev_data_t;
typedef struct { int32_t line_height; ...; } lv_font_t;
typedef struct { uint32_t data_size; uint8_t * data; ...; } lv_draw_buf_t;
typedef struct { ...; } lv_anim_t;
typedef struct _lv_obj_class_t lv_obj_class_t;
typedef struct { uint8_t blue; uint8_t green; uint8_t red; } lv_color_t;

typedef int... lv_state_t;
typedef int... lv_part_t;
typedef int... lv_opa_t;
typedef int... lv_style_prop_t;
typedef int... lv_style_selector_t;
typedef int... lv_obj_flag_t;
typedef int... lv_event_code_t;
typedef int... lv_flex_flow_t;
typedef int... lv_flex_align_t;
typedef int... lv_grid_align_t;
typedef int... lv_dir_t;
typedef int... lv_scrollbar_mode_t;
typedef int... lv_anim_enable_t;
typedef int... lv_label_long_mode_t;
typedef int... lv_image_align_t;
typedef int... lv_bar_mode_t;
typedef int... lv_text_align_t;
typedef int... lv_color_format_t;
typedef int... lv_result_t;
typedef int... lv_text_flag_t;

typedef struct { lv_area_t _clip_area; ...; } lv_layer_t;
typedef int... lv_value_precise_t;
typedef struct { lv_value_precise_t x; lv_value_precise_t y; } lv_point_precise_t;
typedef struct { lv_color_t bg_color; lv_opa_t bg_opa; int32_t radius; ...; } lv_draw_rect_dsc_t;
typedef struct { lv_point_precise_t p1; lv_point_precise_t p2; lv_color_t color; int32_t width; lv_opa_t opa; ...; } lv_draw_line_dsc_t;
typedef struct { const char * text; const lv_font_t * font; lv_color_t color; int32_t rotation; lv_opa_t opa; ...; } lv_draw_label_dsc_t;
typedef struct { const void * src; int32_t rotation; int32_t scale_x; int32_t scale_y; lv_point_t pivot; lv_opa_t opa; ...; } lv_draw_image_dsc_t;

typedef void (*lv_event_cb_t)(lv_event_t * e);
typedef void (*lv_anim_exec_xcb_t)(void *, int32_t);

#define LV_COORD_MAX ...
#define LV_SIZE_CONTENT ...
#define LV_GRID_CONTENT ...
#define LV_GRID_TEMPLATE_LAST ...
#define LV_RADIUS_CIRCLE ...
#define LV_ANIM_REPEAT_INFINITE ...
#define LV_PART_MAIN ...
#define LV_PART_INDICATOR ...
#define LV_STATE_DEFAULT ...
#define LV_STATE_CHECKED ...
#define LV_STATE_DISABLED ...
#define LV_STATE_FOCUSED ...
#define LV_STATE_PRESSED ...
#define LV_OPA_TRANSP ...
#define LV_OPA_COVER ...
#define LV_OPA_40 ...
#define LV_OPA_70 ...

#define LV_OBJ_FLAG_HIDDEN ...
#define LV_OBJ_FLAG_CLICKABLE ...
#define LV_OBJ_FLAG_CLICK_FOCUSABLE ...
#define LV_OBJ_FLAG_SCROLLABLE ...
#define LV_OBJ_FLAG_SCROLL_CHAIN_HOR ...
#define LV_OBJ_FLAG_SCROLL_CHAIN_VER ...
#define LV_OBJ_FLAG_PRESS_LOCK ...
#define LV_OBJ_FLAG_EVENT_BUBBLE ...
#define LV_OBJ_FLAG_IGNORE_LAYOUT ...
#define LV_OBJ_FLAG_FLOATING ...

#define LV_EVENT_ALL ...
#define LV_EVENT_PRESSED ...
#define LV_EVENT_PRESSING ...
#define LV_EVENT_PRESS_LOST ...
#define LV_EVENT_RELEASED ...
#define LV_EVENT_CLICKED ...
#define LV_EVENT_DOUBLE_CLICKED ...
#define LV_EVENT_FOCUSED ...
#define LV_EVENT_DEFOCUSED ...
#define LV_EVENT_VALUE_CHANGED ...
#define LV_EVENT_READY ...
#define LV_EVENT_DELETE ...
#define LV_EVENT_SIZE_CHANGED ...
#define LV_EVENT_STYLE_CHANGED ...
#define LV_EVENT_SCROLL_END ...

#define LV_STYLE_WIDTH ...
#define LV_STYLE_HEIGHT ...
#define LV_STYLE_MIN_WIDTH ...
#define LV_STYLE_MIN_HEIGHT ...
#define LV_STYLE_MAX_WIDTH ...
#define LV_STYLE_MAX_HEIGHT ...
#define LV_STYLE_FLEX_GROW ...
#define LV_STYLE_PAD_TOP ...
#define LV_STYLE_PAD_RIGHT ...
#define LV_STYLE_PAD_BOTTOM ...
#define LV_STYLE_PAD_LEFT ...
#define LV_STYLE_MARGIN_TOP ...
#define LV_STYLE_MARGIN_RIGHT ...
#define LV_STYLE_MARGIN_BOTTOM ...
#define LV_STYLE_MARGIN_LEFT ...
#define LV_STYLE_TEXT_COLOR ...
#define LV_STYLE_TEXT_OPA ...
#define LV_STYLE_TEXT_FONT ...
#define LV_STYLE_BG_COLOR ...
#define LV_STYLE_BG_OPA ...

#define LV_LAYOUT_FLEX ...
#define LV_LAYOUT_GRID ...
#define LV_FLEX_COLUMN ...
#define LV_FLEX_FLOW_ROW ...
#define LV_FLEX_FLOW_COLUMN ...
#define LV_FLEX_FLOW_ROW_REVERSE ...
#define LV_FLEX_FLOW_COLUMN_REVERSE ...
#define LV_FLEX_ALIGN_START ...
#define LV_FLEX_ALIGN_CENTER ...
#define LV_FLEX_ALIGN_END ...
#define LV_GRID_ALIGN_START ...
#define LV_GRID_ALIGN_CENTER ...
#define LV_GRID_ALIGN_END ...
#define LV_GRID_ALIGN_STRETCH ...
#define LV_DIR_NONE ...
#define LV_DIR_HOR ...
#define LV_DIR_VER ...
#define LV_DIR_ALL ...
#define LV_SCROLLBAR_MODE_OFF ...
#define LV_SCROLLBAR_MODE_ON ...
#define LV_SCROLLBAR_MODE_AUTO ...
#define LV_ANIM_OFF ...
#define LV_LABEL_LONG_MODE_WRAP ...
#define LV_LABEL_LONG_MODE_CLIP ...
#define LV_IMAGE_ALIGN_CONTAIN ...
#define LV_IMAGE_ALIGN_STRETCH ...
#define LV_BAR_MODE_NORMAL ...
#define LV_BAR_MODE_RANGE ...
#define LV_TEXT_ALIGN_LEFT ...
#define LV_TEXT_ALIGN_CENTER ...
#define LV_COLOR_FORMAT_ARGB8888 ...
#define LV_RESULT_OK ...

/* Display / screen / group */
lv_display_t * lv_display_get_default(void);
int32_t lv_display_get_horizontal_resolution(const lv_display_t * disp);
int32_t lv_display_get_vertical_resolution(const lv_display_t * disp);
lv_obj_t * lv_screen_active(void);
lv_group_t * lv_group_get_default(void);
void lv_group_focus_obj(lv_obj_t * obj);
lv_group_t * lv_obj_get_group(const lv_obj_t * obj);

#define LV_INDEV_TYPE_POINTER ...
#define LV_INDEV_TYPE_KEYPAD ...
#define LV_INDEV_STATE_PRESSED ...
#define LV_INDEV_STATE_RELEASED ...
extern "Python" void _pui_test_pointer_cb(lv_indev_t * indev, lv_indev_data_t * data);
lv_indev_t * lv_indev_create(void);
void lv_indev_delete(lv_indev_t * indev);
void lv_indev_read(lv_indev_t * indev);
void lv_indev_set_type(lv_indev_t * indev, lv_indev_type_t indev_type);
void lv_indev_set_read_cb(lv_indev_t * indev, void (*read_cb)(lv_indev_t *, lv_indev_data_t *));
void lv_obj_get_coords(const lv_obj_t * obj, lv_area_t * coords);
lv_indev_t * lv_indev_active(void);
void lv_indev_get_point(const lv_indev_t * indev, lv_point_t * point);

const lv_obj_class_t * lv_obj_get_class(const lv_obj_t * obj);
bool lv_obj_check_type(const lv_obj_t * obj, const lv_obj_class_t * class_p);

/* Tree */
lv_obj_t * lv_obj_create(lv_obj_t * parent);
void lv_obj_delete(lv_obj_t * obj);
void lv_obj_clean(lv_obj_t * obj);
bool lv_obj_is_valid(const lv_obj_t * obj);
lv_obj_t * lv_obj_get_parent(const lv_obj_t * obj);
uint32_t lv_obj_get_child_count(const lv_obj_t * obj);
lv_obj_t * lv_obj_get_child(const lv_obj_t * obj, int32_t idx);
void lv_obj_move_to_index(lv_obj_t * obj, int32_t index);
int32_t lv_obj_get_index(const lv_obj_t * obj);

/* Flags / state */
void lv_obj_add_flag(lv_obj_t * obj, lv_obj_flag_t f);
void lv_obj_remove_flag(lv_obj_t * obj, lv_obj_flag_t f);
bool lv_obj_has_flag(const lv_obj_t * obj, lv_obj_flag_t f);
void lv_obj_set_state(lv_obj_t * obj, lv_state_t state, bool v);
bool lv_obj_has_state(const lv_obj_t * obj, lv_state_t state);

/* Geometry */
int32_t lv_pct(int32_t x);
void lv_obj_set_width(lv_obj_t * obj, int32_t w);
void lv_obj_set_height(lv_obj_t * obj, int32_t h);
void lv_obj_set_size(lv_obj_t * obj, int32_t w, int32_t h);
void lv_obj_set_pos(lv_obj_t * obj, int32_t x, int32_t y);
int32_t lv_obj_get_x(const lv_obj_t * obj);
int32_t lv_obj_get_y(const lv_obj_t * obj);
int32_t lv_obj_get_width(const lv_obj_t * obj);
int32_t lv_obj_get_height(const lv_obj_t * obj);
int32_t lv_obj_get_content_width(const lv_obj_t * obj);
int32_t lv_obj_get_content_height(const lv_obj_t * obj);
void lv_obj_update_layout(const lv_obj_t * obj);
void lv_obj_mark_layout_as_dirty(lv_obj_t * obj);
void lv_obj_center(lv_obj_t * obj);

/* Layouts */
void lv_obj_set_flex_flow(lv_obj_t * obj, lv_flex_flow_t flow);
void lv_obj_set_flex_align(lv_obj_t * obj, lv_flex_align_t main_place, lv_flex_align_t cross_place, lv_flex_align_t track_cross_place);
void lv_obj_set_flex_grow(lv_obj_t * obj, uint8_t grow);
void lv_obj_set_grid_dsc_array(lv_obj_t * obj, const int32_t col_dsc[], const int32_t row_dsc[]);
void lv_obj_set_grid_cell(lv_obj_t * obj, lv_grid_align_t x_align, int32_t col_pos, int32_t col_span,
                          lv_grid_align_t y_align, int32_t row_pos, int32_t row_span);

/* Styles */
lv_color_t lv_color_hex(uint32_t c);
void lv_obj_remove_style_all(lv_obj_t * obj);
bool lv_obj_remove_local_style_prop(lv_obj_t * obj, lv_style_prop_t prop, lv_style_selector_t selector);
void lv_obj_set_style_min_width(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_min_height(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_max_width(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_max_height(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_pad_all(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_pad_top(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_pad_right(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_pad_bottom(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_pad_left(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_pad_row(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_pad_column(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_margin_top(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_margin_right(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_margin_bottom(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_margin_left(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_bg_color(lv_obj_t * obj, lv_color_t value, lv_style_selector_t selector);
void lv_obj_set_style_bg_opa(lv_obj_t * obj, lv_opa_t value, lv_style_selector_t selector);
void lv_obj_set_style_bg_image_src(lv_obj_t * obj, const void * value, lv_style_selector_t selector);
void lv_obj_set_style_text_color(lv_obj_t * obj, lv_color_t value, lv_style_selector_t selector);
void lv_obj_set_style_text_opa(lv_obj_t * obj, lv_opa_t value, lv_style_selector_t selector);
void lv_obj_set_style_text_font(lv_obj_t * obj, const lv_font_t * value, lv_style_selector_t selector);
void lv_obj_set_style_text_align(lv_obj_t * obj, lv_text_align_t value, lv_style_selector_t selector);
void lv_obj_set_style_border_width(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_border_color(lv_obj_t * obj, lv_color_t value, lv_style_selector_t selector);
void lv_obj_set_style_radius(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
void lv_obj_set_style_shadow_width(lv_obj_t * obj, int32_t value, lv_style_selector_t selector);
int32_t lv_obj_get_style_width(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_height(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_min_width(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_min_height(const lv_obj_t * obj, lv_part_t part);
uint8_t lv_obj_get_style_flex_grow(const lv_obj_t * obj, lv_part_t part);
lv_flex_flow_t lv_obj_get_style_flex_flow(const lv_obj_t * obj, lv_part_t part);
uint16_t lv_obj_get_style_layout(const lv_obj_t * obj, lv_part_t part);
lv_grid_align_t lv_obj_get_style_grid_cell_x_align(const lv_obj_t * obj, lv_part_t part);
lv_grid_align_t lv_obj_get_style_grid_cell_y_align(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_pad_row(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_pad_column(const lv_obj_t * obj, lv_part_t part);

int32_t lv_obj_get_style_space_left(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_space_right(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_space_top(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_space_bottom(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_margin_left(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_margin_right(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_margin_top(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_margin_bottom(const lv_obj_t * obj, lv_part_t part);
const lv_font_t * lv_obj_get_style_text_font(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_text_letter_space(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_text_line_space(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_calc_dynamic_width(lv_obj_t * obj, lv_style_prop_t prop);
int32_t lv_obj_calc_dynamic_height(lv_obj_t * obj, lv_style_prop_t prop);
bool lv_obj_refresh_self_size(lv_obj_t * obj);
void lv_text_get_size(lv_point_t * size_res, const char * text, const lv_font_t * font, int32_t letter_space,
                      int32_t line_space, int32_t max_width, lv_text_flag_t flag);

/* Scrolling */
void lv_obj_set_scroll_dir(lv_obj_t * obj, lv_dir_t dir);
void lv_obj_set_scrollbar_mode(lv_obj_t * obj, lv_scrollbar_mode_t mode);
void lv_obj_scroll_to(lv_obj_t * obj, int32_t x, int32_t y, lv_anim_enable_t anim_en);
int32_t lv_obj_get_scroll_x(const lv_obj_t * obj);
int32_t lv_obj_get_scroll_y(const lv_obj_t * obj);
int32_t lv_obj_get_scroll_right(lv_obj_t * obj);
int32_t lv_obj_get_scroll_bottom(lv_obj_t * obj);
void lv_obj_stop_scroll_anim(const lv_obj_t * obj);
void lv_obj_scroll_to_view_recursive(lv_obj_t * obj, lv_anim_enable_t anim_en);
void lv_obj_readjust_scroll(lv_obj_t * obj, lv_anim_enable_t anim_en);

/* Events */
extern "Python" void _pui_event_cb(lv_event_t * e);
lv_event_dsc_t * lv_obj_add_event_cb(lv_obj_t * obj, lv_event_cb_t event_cb, lv_event_code_t filter, void * user_data);
uint32_t lv_obj_remove_event_cb_with_user_data(lv_obj_t * obj, lv_event_cb_t event_cb, void * user_data);
lv_event_code_t lv_event_get_code(lv_event_t * e);
void * lv_event_get_user_data(lv_event_t * e);
void * lv_event_get_param(lv_event_t * e);
lv_obj_t * lv_event_get_target_obj(lv_event_t * e);
lv_result_t lv_obj_send_event(lv_obj_t * obj, lv_event_code_t event_code, void * param);

/* Animation */
extern "Python" void _pui_anim_busy_cb(void * var, int32_t value);
void lv_anim_init(lv_anim_t * a);
void lv_anim_set_var(lv_anim_t * a, void * var);
void lv_anim_set_exec_cb(lv_anim_t * a, lv_anim_exec_xcb_t exec_cb);
void lv_anim_set_values(lv_anim_t * a, int32_t start, int32_t end);
void lv_anim_set_duration(lv_anim_t * a, uint32_t duration);
void lv_anim_set_reverse_duration(lv_anim_t * a, uint32_t duration);
void lv_anim_set_repeat_count(lv_anim_t * a, uint32_t cnt);
lv_anim_t * lv_anim_start(const lv_anim_t * a);
bool lv_anim_delete(void * var, lv_anim_exec_xcb_t exec_cb);
lv_anim_t * lv_anim_get(void * var, lv_anim_exec_xcb_t exec_cb);

/* Fonts */
extern lv_font_t lv_font_montserrat_8;
extern lv_font_t lv_font_montserrat_10;
extern lv_font_t lv_font_montserrat_12;
extern lv_font_t lv_font_montserrat_14;
extern lv_font_t lv_font_montserrat_16;
extern lv_font_t lv_font_montserrat_18;
extern lv_font_t lv_font_montserrat_20;
extern lv_font_t lv_font_montserrat_22;
extern lv_font_t lv_font_montserrat_24;
extern lv_font_t lv_font_montserrat_26;
extern lv_font_t lv_font_montserrat_28;
extern lv_font_t lv_font_montserrat_30;
extern lv_font_t lv_font_montserrat_32;
extern lv_font_t lv_font_montserrat_34;
extern lv_font_t lv_font_montserrat_36;
extern lv_font_t lv_font_montserrat_38;
extern lv_font_t lv_font_montserrat_40;
extern lv_font_t lv_font_montserrat_42;
extern lv_font_t lv_font_montserrat_44;
extern lv_font_t lv_font_montserrat_46;
extern lv_font_t lv_font_montserrat_48;

/* Widgets */
lv_obj_t * lv_label_create(lv_obj_t * parent);
void lv_label_set_text(lv_obj_t * obj, const char * text);
char * lv_label_get_text(const lv_obj_t * obj);
void lv_label_set_long_mode(lv_obj_t * obj, lv_label_long_mode_t long_mode);

lv_obj_t * lv_button_create(lv_obj_t * parent);

lv_obj_t * lv_checkbox_create(lv_obj_t * parent);
void lv_checkbox_set_text(lv_obj_t * obj, const char * txt);

lv_obj_t * lv_image_create(lv_obj_t * parent);
void lv_image_set_src(lv_obj_t * obj, const void * src);
void lv_image_set_inner_align(lv_obj_t * obj, lv_image_align_t align);
void lv_image_set_antialias(lv_obj_t * obj, bool antialias);
int32_t lv_image_get_src_width(lv_obj_t * obj);
int32_t lv_image_get_src_height(lv_obj_t * obj);

lv_obj_t * lv_bar_create(lv_obj_t * parent);
void lv_bar_set_value(lv_obj_t * obj, int32_t value, lv_anim_enable_t anim);
void lv_bar_set_start_value(lv_obj_t * obj, int32_t start_value, lv_anim_enable_t anim);
void lv_bar_set_range(lv_obj_t * obj, int32_t min, int32_t max);
void lv_bar_set_mode(lv_obj_t * obj, lv_bar_mode_t mode);

lv_obj_t * lv_textarea_create(lv_obj_t * parent);
void lv_textarea_set_text(lv_obj_t * obj, const char * txt);
const char * lv_textarea_get_text(const lv_obj_t * obj);
void lv_textarea_add_text(lv_obj_t * obj, const char * txt);
void lv_textarea_set_one_line(lv_obj_t * obj, bool en);
void lv_textarea_set_placeholder_text(lv_obj_t * obj, const char * txt);
void lv_textarea_set_password_mode(lv_obj_t * obj, bool en);

lv_obj_t * lv_dropdown_create(lv_obj_t * parent);
void lv_dropdown_set_options(lv_obj_t * obj, const char * options);
void lv_dropdown_set_selected(lv_obj_t * obj, uint32_t sel_opt);
uint32_t lv_dropdown_get_selected(const lv_obj_t * obj);
void lv_dropdown_close(lv_obj_t * obj);
void lv_dropdown_set_text(lv_obj_t * obj, const char * text);

/* Canvas / drawing */
#define LV_SCALE_NONE ...
#define LV_STRIDE_AUTO ...
lv_obj_t * lv_canvas_create(lv_obj_t * parent);
void lv_canvas_set_draw_buf(lv_obj_t * obj, lv_draw_buf_t * draw_buf);
void lv_canvas_fill_bg(lv_obj_t * obj, lv_color_t color, lv_opa_t opa);
void lv_canvas_init_layer(lv_obj_t * obj, lv_layer_t * layer);
void lv_canvas_finish_layer(lv_obj_t * canvas, lv_layer_t * layer);
lv_draw_buf_t * lv_draw_buf_create(uint32_t w, uint32_t h, lv_color_format_t cf, uint32_t stride);
void lv_draw_buf_clear(lv_draw_buf_t * draw_buf, const lv_area_t * a);
void lv_draw_rect_dsc_init(lv_draw_rect_dsc_t * dsc);
void lv_draw_rect(lv_layer_t * layer, const lv_draw_rect_dsc_t * dsc, const lv_area_t * coords);
void lv_draw_line_dsc_init(lv_draw_line_dsc_t * dsc);
void lv_draw_line(lv_layer_t * layer, const lv_draw_line_dsc_t * dsc);
void lv_draw_label_dsc_init(lv_draw_label_dsc_t * dsc);
void lv_draw_label(lv_layer_t * layer, const lv_draw_label_dsc_t * dsc, const lv_area_t * coords);
void lv_draw_image_dsc_init(lv_draw_image_dsc_t * dsc);
void lv_draw_image(lv_layer_t * layer, const lv_draw_image_dsc_t * dsc, const lv_area_t * coords);
lv_indev_t * lv_indev_get_next(lv_indev_t * indev);
lv_indev_type_t lv_indev_get_type(const lv_indev_t * indev);
lv_obj_t * lv_indev_search_obj(lv_obj_t * obj, lv_point_t * point);
#define LV_EVENT_ROTARY ...

/* Table */
#define LV_PART_ITEMS ...
#define LV_TABLE_CELL_NONE ...
lv_obj_t * lv_table_create(lv_obj_t * parent);
void lv_table_set_cell_value(lv_obj_t * obj, uint32_t row, uint32_t col, const char * txt);
void lv_table_set_row_count(lv_obj_t * obj, uint32_t row_cnt);
void lv_table_set_column_count(lv_obj_t * obj, uint32_t col_cnt);
void lv_table_set_column_width(lv_obj_t * obj, uint32_t col_id, int32_t w);
const char * lv_table_get_cell_value(lv_obj_t * obj, uint32_t row, uint32_t col);
uint32_t lv_table_get_row_count(lv_obj_t * obj);
uint32_t lv_table_get_column_count(lv_obj_t * obj);
void lv_table_get_selected_cell(lv_obj_t * obj, uint32_t * row, uint32_t * col);
void lv_table_set_selected_cell(lv_obj_t * obj, uint16_t row, uint16_t col);
int32_t lv_obj_get_style_pad_left(const lv_obj_t * obj, lv_part_t part);
int32_t lv_obj_get_style_pad_right(const lv_obj_t * obj, lv_part_t part);

/* Overlays */
#define LV_ALIGN_CENTER ...
#define LV_ALIGN_TOP_LEFT ...
#define LV_ALIGN_OUT_BOTTOM_LEFT ...
#define LV_ALIGN_OUT_RIGHT_TOP ...
lv_obj_t * lv_layer_top(void);
void lv_obj_align(lv_obj_t * obj, int align, int32_t x_ofs, int32_t y_ofs);
void lv_obj_align_to(lv_obj_t * obj, const lv_obj_t * base, int align, int32_t x_ofs, int32_t y_ofs);
void lv_obj_scroll_to_view(lv_obj_t * obj, lv_anim_enable_t anim_en);

/* Snapshot */
lv_draw_buf_t * lv_snapshot_take(lv_obj_t * obj, lv_color_format_t cf);
void lv_draw_buf_destroy(lv_draw_buf_t * draw_buf);
""")

# ---- set_source: point at our C wrapper ----

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
csrc_dir = os.path.join(project_root, "csrc")
lvgl_path = os.environ.get("LVGL_PATH", os.path.join(project_root, "lvgl-9.6.0"))
drivers = sorted(set(d.lower() for d in os.environ.get("PUI_DRV", "sdl2").split()))
suffix = "_".join(drivers)
module_name = "PUI.lvgl.liblvgl_" + suffix

lv_conf_path = os.path.join(csrc_dir, "lv_conf.h")

build_dir = os.environ.get("PUI_LVGL_BUILD_DIR", os.path.join(project_root, "build-lvgl-" + suffix))

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
extra_compile_args = []

import subprocess

for drv in drivers:
    drv = drv.lower()
    define_macros.append(("PUI_DRV_" + drv.upper(), "1"))
    src = os.path.join(csrc_dir, f"driver_{drv}.c")
    if os.path.exists(src):
        sources.append(src)

    package = {"sdl2": "sdl2", "x11": "x11"}.get(drv)
    if package:
        try:
            extra_compile_args.extend(subprocess.check_output(["pkg-config", "--cflags", package], text=True).split())
            extra_link_args.extend(subprocess.check_output(["pkg-config", "--libs", package], text=True).split())
        except (subprocess.CalledProcessError, FileNotFoundError):
            libraries.append({"sdl2": "SDL2", "x11": "X11"}[drv])

ffi.set_source(
    module_name,
    '#include "pui_lvgl.h"',
    sources=sources,
    include_dirs=include_dirs,
    library_dirs=library_dirs,
    libraries=libraries,
    define_macros=define_macros,
    extra_link_args=extra_link_args,
    extra_compile_args=extra_compile_args,
)

if __name__ == "__main__":
    # Intermediate C/object files stay in the build dir; the extension module
    # itself is written next to this script.
    tmpdir = os.path.join(build_dir, "cffi")
    built = ffi.compile(tmpdir=tmpdir, verbose=True)
    import shutil
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(built))
    shutil.copy2(built, target)
    print("built", target)
