#ifndef PUI_LVGL_H
#define PUI_LVGL_H

#include <stdint.h>

/* ---- Initialization / event loop ---- */

/* Parse "driver#key=val#..." and bring up the display.
   Returns 0 on success, -1 on error. */
int  pui_lvgl_init(const char *driver_config);
void pui_lvgl_deinit(void);

/* Run one LVGL timer tick; returns ms until next call is useful.
   The Python side calls this in a loop for the main-loop. */
uint32_t pui_lvgl_timer_handler(void);

/* Non-zero while the display is still alive. */
int pui_lvgl_is_running(void);

/* ---- Screen ---- */
void *pui_lvgl_screen_active(void);

/* ---- Object lifecycle ---- */
void *pui_lv_obj_create(void *parent);
void  pui_lv_obj_delete(void *obj);
void  pui_lv_obj_clean(void *obj);

/* ---- Label ---- */
void *pui_lv_label_create(void *parent);
void  pui_lv_label_set_text(void *obj, const char *text);

/* ---- Button ---- */
void *pui_lv_btn_create(void *parent);
void *pui_lv_btn_get_or_create_label(void *btn);

/* ---- Checkbox ---- */
void *pui_lv_checkbox_create(void *parent);
void  pui_lv_checkbox_set_text(void *obj, const char *text);
void  pui_lv_checkbox_set_checked(void *obj, int checked);
int   pui_lv_checkbox_is_checked(void *obj);

/* ---- Image ---- */
void *pui_lv_image_create(void *parent);
void  pui_lv_image_set_src_file(void *obj, const char *path);

/* ---- ProgressBar ---- */
void *pui_lv_bar_create(void *parent);
void  pui_lv_bar_set_value(void *obj, int value);
void  pui_lv_bar_set_range(void *obj, int min, int max);

/* ---- TextField ---- */
void *pui_lv_textarea_create(void *parent);
void  pui_lv_textarea_set_text(void *obj, const char *text);
const char *pui_lv_textarea_get_text(void *obj);
void  pui_lv_textarea_set_one_line(void *obj, int one_line);
void  pui_lv_textarea_set_placeholder(void *obj, const char *text);

/* ---- Scroll container ---- */
void *pui_lv_scroll_create(void *parent);

/* ---- Size / position ---- */
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

/* ---- Flex layout ---- */
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

/* ---- Grid layout ---- */
void pui_lv_obj_set_grid(void *obj, int cols, int rows);
void pui_lv_obj_set_grid_cell(void *obj, int col, int row, int colspan, int rowspan);

/* ---- Style ---- */
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

/* Transparent background helper */
void pui_lv_obj_set_transparent(void *obj);

/* ---- Visibility ---- */
void pui_lv_obj_set_hidden(void *obj, int hidden);
void pui_lv_obj_set_clickable(void *obj, int clickable);
void pui_lv_obj_set_scrollable(void *obj, int scrollable);
void pui_lv_obj_set_disabled(void *obj, int disabled);

/* ---- Child ordering ---- */
void pui_lv_obj_move_to_index(void *obj, int index);
void pui_lv_obj_center(void *obj);

/* ---- Events ---- */
#define PUI_EVENT_CLICKED      1
#define PUI_EVENT_VALUE_CHANGED 2
#define PUI_EVENT_READY        3
#define PUI_EVENT_DELETE        100

typedef void (*pui_event_cb_t)(int event_code, void *user_data);

void *pui_lv_obj_add_event_cb(void *obj, pui_event_cb_t cb, void *user_data);
void  pui_lv_obj_remove_event_cb(void *obj, void *descriptor);

/* ---- Timer / command poster ---- */
void *pui_lv_timer_create(void (*cb)(void *), int period_ms, void *user_data);
void  pui_lv_timer_delete(void *timer);

/* ---- Helpers ---- */

/* Parse "driver#k=v#..." — exposed so Python tests can validate format. */
const char *pui_parse_driver_name(const char *config);

#endif /* PUI_LVGL_H */
