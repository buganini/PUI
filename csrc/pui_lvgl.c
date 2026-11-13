#include "pui_lvgl.h"
#include <lvgl.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

/* ---- Driver config parsing (same logic as alarm's parse_driver_profile) ---- */

typedef struct {
    char driver[32];
    int  width, height;
    int  rotation;
    int  x_offset, y_offset;
    int  flip_x, flip_y;
    int  color_invert;
    int  spi_bus, spi_device;
    int  dc, cs, reset, backlight;
    int  baudrate;
} pui_display_config_t;

static void config_defaults(pui_display_config_t *cfg)
{
    memset(cfg, 0, sizeof(*cfg));
    cfg->width = 800;
    cfg->height = 600;
    cfg->rotation = 0;
    cfg->spi_bus = 0;
    cfg->spi_device = 0;
    cfg->dc = -1;
    cfg->cs = -1;
    cfg->reset = -1;
    cfg->backlight = -1;
    cfg->baudrate = 24000000;
}

static int parse_bool(const char *val)
{
    return strcmp(val, "true") == 0 || strcmp(val, "1") == 0 || strcmp(val, "yes") == 0;
}

static int parse_driver_config(const char *input, pui_display_config_t *cfg)
{
    config_defaults(cfg);
    if (!input || !*input) {
        strcpy(cfg->driver, "sdl2");
        return 0;
    }
    /* Work on a copy so we can tokenize. */
    char *buf = strdup(input);
    if (!buf) return -1;

    char *saveptr = NULL;
    char *token = strtok_r(buf, "#", &saveptr);
    if (token) {
        snprintf(cfg->driver, sizeof(cfg->driver), "%s", token);
        /* Lowercase the driver name. */
        for (char *p = cfg->driver; *p; ++p)
            if (*p >= 'A' && *p <= 'Z') *p += 32;
    }

    while ((token = strtok_r(NULL, "#", &saveptr)) != NULL) {
        char *eq = strchr(token, '=');
        if (!eq) continue;
        *eq = '\0';
        const char *key = token;
        const char *val = eq + 1;

        if      (strcmp(key, "width") == 0)        cfg->width = atoi(val);
        else if (strcmp(key, "height") == 0)       cfg->height = atoi(val);
        else if (strcmp(key, "rotation") == 0 || strcmp(key, "rotate") == 0) cfg->rotation = atoi(val);
        else if (strcmp(key, "x_offset") == 0)     cfg->x_offset = atoi(val);
        else if (strcmp(key, "y_offset") == 0)     cfg->y_offset = atoi(val);
        else if (strcmp(key, "flip_x") == 0)       cfg->flip_x = parse_bool(val);
        else if (strcmp(key, "flip_y") == 0)       cfg->flip_y = parse_bool(val);
        else if (strcmp(key, "color_invert") == 0) cfg->color_invert = parse_bool(val);
        else if (strcmp(key, "spi_bus") == 0)      cfg->spi_bus = atoi(val);
        else if (strcmp(key, "spi_device") == 0)   cfg->spi_device = atoi(val);
        else if (strcmp(key, "dc") == 0)           cfg->dc = atoi(val);
        else if (strcmp(key, "cs") == 0)           cfg->cs = atoi(val);
        else if (strcmp(key, "reset") == 0)        cfg->reset = atoi(val);
        else if (strcmp(key, "backlight") == 0)    cfg->backlight = atoi(val);
        else if (strcmp(key, "baudrate") == 0)     cfg->baudrate = atoi(val);
    }
    free(buf);
    return 0;
}

/* ---- Global state ---- */

static lv_display_t *s_display = NULL;
static int s_running = 0;
static pui_display_config_t s_config;

/* Forward declarations for drivers (defined in drv_*.c, linked at build time). */
#ifdef PUI_DRV_SDL2
extern lv_display_t *pui_drv_sdl2_init(int w, int h);
extern void pui_drv_sdl2_deinit(void);
#endif
#ifdef PUI_DRV_X11
extern lv_display_t *pui_drv_x11_init(int w, int h, const char *title);
extern void pui_drv_x11_deinit(void);
#endif
#ifdef PUI_DRV_SPI
extern lv_display_t *pui_drv_spi_init(const pui_display_config_t *cfg);
extern void pui_drv_spi_deinit(void);
#endif

/* ---- Init / deinit ---- */

int pui_lvgl_init(const char *driver_config)
{
    if (s_running) return 0;

    if (parse_driver_config(driver_config, &s_config) != 0)
        return -1;

    lv_init();

    lv_display_t *disp = NULL;
#ifdef PUI_DRV_SDL2
    if (strcmp(s_config.driver, "sdl2") == 0)
        disp = pui_drv_sdl2_init(s_config.width, s_config.height);
#endif
#ifdef PUI_DRV_X11
    if (strcmp(s_config.driver, "x11") == 0)
        disp = pui_drv_x11_init(s_config.width, s_config.height, "PUI LVGL");
#endif
#ifdef PUI_DRV_SPI
    if (strcmp(s_config.driver, "ili9341") == 0 || strcmp(s_config.driver, "st7789") == 0)
        disp = pui_drv_spi_init(&s_config);
#endif
    if (!disp) {
        fprintf(stderr, "pui_lvgl: unsupported or unavailable driver '%s'\n", s_config.driver);
        lv_deinit();
        return -1;
    }
    s_display = disp;
    s_running = 1;
    return 0;
}

void pui_lvgl_deinit(void)
{
    if (!s_running) return;
    s_running = 0;
#ifdef PUI_DRV_SDL2
    if (strcmp(s_config.driver, "sdl2") == 0) pui_drv_sdl2_deinit();
#endif
#ifdef PUI_DRV_X11
    if (strcmp(s_config.driver, "x11") == 0) pui_drv_x11_deinit();
#endif
#ifdef PUI_DRV_SPI
    if (strcmp(s_config.driver, "ili9341") == 0 || strcmp(s_config.driver, "st7789") == 0)
        pui_drv_spi_deinit();
#endif
    s_display = NULL;
    lv_deinit();
}

uint32_t pui_lvgl_timer_handler(void)
{
    if (!s_running) return 100;
    return lv_timer_handler();
}

int pui_lvgl_is_running(void)
{
    return s_running && lv_display_get_next(NULL) != NULL;
}

/* ---- Screen ---- */

void *pui_lvgl_screen_active(void)
{
    return (void *)lv_screen_active();
}

/* ---- Object lifecycle ---- */

void *pui_lv_obj_create(void *parent)
{
    return (void *)lv_obj_create((lv_obj_t *)parent);
}

void pui_lv_obj_delete(void *obj)
{
    if (obj) lv_obj_delete((lv_obj_t *)obj);
}

void pui_lv_obj_clean(void *obj)
{
    if (obj) lv_obj_clean((lv_obj_t *)obj);
}

/* ---- Label ---- */

void *pui_lv_label_create(void *parent)
{
    return (void *)lv_label_create((lv_obj_t *)parent);
}

void pui_lv_label_set_text(void *obj, const char *text)
{
    lv_label_set_text((lv_obj_t *)obj, text);
}

/* ---- Button ---- */

void *pui_lv_btn_create(void *parent)
{
    return (void *)lv_button_create((lv_obj_t *)parent);
}

void *pui_lv_btn_get_or_create_label(void *btn)
{
    lv_obj_t *b = (lv_obj_t *)btn;
    /* If button already has a label child, return it. */
    uint32_t count = lv_obj_get_child_count(b);
    for (uint32_t i = 0; i < count; i++) {
        lv_obj_t *child = lv_obj_get_child(b, i);
        if (lv_obj_check_type(child, &lv_label_class))
            return (void *)child;
    }
    lv_obj_t *label = lv_label_create(b);
    lv_obj_center(label);
    return (void *)label;
}

/* ---- Checkbox ---- */

void *pui_lv_checkbox_create(void *parent)
{
    return (void *)lv_checkbox_create((lv_obj_t *)parent);
}

void pui_lv_checkbox_set_text(void *obj, const char *text)
{
    lv_checkbox_set_text((lv_obj_t *)obj, text);
}

void pui_lv_checkbox_set_checked(void *obj, int checked)
{
    if (checked)
        lv_obj_add_state((lv_obj_t *)obj, LV_STATE_CHECKED);
    else
        lv_obj_remove_state((lv_obj_t *)obj, LV_STATE_CHECKED);
}

int pui_lv_checkbox_is_checked(void *obj)
{
    return (lv_obj_get_state((lv_obj_t *)obj) & LV_STATE_CHECKED) != 0;
}

/* ---- Image ---- */

void *pui_lv_image_create(void *parent)
{
    return (void *)lv_image_create((lv_obj_t *)parent);
}

void pui_lv_image_set_src_file(void *obj, const char *path)
{
    /* LVGL file paths are prefixed with a drive letter; 'A:' for the default FS. */
    static char buf[1024];
    snprintf(buf, sizeof(buf), "A:%s", path);
    lv_image_set_src((lv_obj_t *)obj, buf);
}

/* ---- ProgressBar ---- */

void *pui_lv_bar_create(void *parent)
{
    return (void *)lv_bar_create((lv_obj_t *)parent);
}

void pui_lv_bar_set_value(void *obj, int value)
{
    lv_bar_set_value((lv_obj_t *)obj, value, LV_ANIM_OFF);
}

void pui_lv_bar_set_range(void *obj, int min, int max)
{
    lv_bar_set_range((lv_obj_t *)obj, min, max);
}

/* ---- TextField ---- */

void *pui_lv_textarea_create(void *parent)
{
    return (void *)lv_textarea_create((lv_obj_t *)parent);
}

void pui_lv_textarea_set_text(void *obj, const char *text)
{
    lv_textarea_set_text((lv_obj_t *)obj, text);
}

const char *pui_lv_textarea_get_text(void *obj)
{
    return lv_textarea_get_text((lv_obj_t *)obj);
}

void pui_lv_textarea_set_one_line(void *obj, int one_line)
{
    lv_textarea_set_one_line((lv_obj_t *)obj, one_line != 0);
}

void pui_lv_textarea_set_placeholder(void *obj, const char *text)
{
    lv_textarea_set_placeholder_text((lv_obj_t *)obj, text);
}

/* ---- Scroll ---- */

void *pui_lv_scroll_create(void *parent)
{
    lv_obj_t *obj = lv_obj_create((lv_obj_t *)parent);
    lv_obj_set_scroll_dir(obj, LV_DIR_VER);
    lv_obj_set_style_bg_opa(obj, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(obj, 0, 0);
    return (void *)obj;
}

/* ---- Size / position ---- */

void pui_lv_obj_set_width(void *obj, int w)       { lv_obj_set_width((lv_obj_t *)obj, w); }
void pui_lv_obj_set_height(void *obj, int h)      { lv_obj_set_height((lv_obj_t *)obj, h); }
void pui_lv_obj_set_size(void *obj, int w, int h)  { lv_obj_set_size((lv_obj_t *)obj, w, h); }
void pui_lv_obj_set_size_content(void *obj)        { lv_obj_set_size((lv_obj_t *)obj, LV_SIZE_CONTENT, LV_SIZE_CONTENT); }
void pui_lv_obj_set_width_pct(void *obj, int pct)  { lv_obj_set_width((lv_obj_t *)obj, lv_pct(pct)); }
void pui_lv_obj_set_height_pct(void *obj, int pct) { lv_obj_set_height((lv_obj_t *)obj, lv_pct(pct)); }
void pui_lv_obj_set_min_width(void *obj, int w)    { lv_obj_set_style_min_width((lv_obj_t *)obj, w, 0); }
void pui_lv_obj_set_min_height(void *obj, int h)   { lv_obj_set_style_min_height((lv_obj_t *)obj, h, 0); }

int pui_lv_obj_get_width(void *obj)           { return lv_obj_get_width((lv_obj_t *)obj); }
int pui_lv_obj_get_height(void *obj)          { return lv_obj_get_height((lv_obj_t *)obj); }
int pui_lv_obj_get_content_width(void *obj)   { return lv_obj_get_content_width((lv_obj_t *)obj); }
int pui_lv_obj_get_content_height(void *obj)  { return lv_obj_get_content_height((lv_obj_t *)obj); }

/* ---- Flex layout ---- */

static lv_flex_flow_t flex_flow_map[] = {
    LV_FLEX_FLOW_ROW,            /* 0 */
    LV_FLEX_FLOW_COLUMN,         /* 1 */
    LV_FLEX_FLOW_ROW_REVERSE,    /* 2 */
    LV_FLEX_FLOW_COLUMN_REVERSE, /* 3 */
};

static lv_flex_align_t flex_align_map[] = {
    LV_FLEX_ALIGN_START,   /* 0 */
    LV_FLEX_ALIGN_CENTER,  /* 1 */
    LV_FLEX_ALIGN_END,     /* 2 */
};

void pui_lv_obj_set_flex_flow(void *obj, int flow)
{
    if (flow >= 0 && flow < 4)
        lv_obj_set_flex_flow((lv_obj_t *)obj, flex_flow_map[flow]);
}

void pui_lv_obj_set_flex_grow(void *obj, int grow)
{
    lv_obj_set_flex_grow((lv_obj_t *)obj, grow);
}

void pui_lv_obj_set_flex_align(void *obj, int main_place, int cross_place, int track_place)
{
    lv_obj_set_flex_align((lv_obj_t *)obj,
        main_place >= 0 && main_place < 3 ? flex_align_map[main_place] : LV_FLEX_ALIGN_START,
        cross_place >= 0 && cross_place < 3 ? flex_align_map[cross_place] : LV_FLEX_ALIGN_START,
        track_place >= 0 && track_place < 3 ? flex_align_map[track_place] : LV_FLEX_ALIGN_START);
}

/* ---- Grid layout ---- */

/* Simplified grid: uniform FR columns and FR rows.
   For PUI's grid, the Python side manages placement. */
static int32_t s_grid_col_dsc[64 + 1];
static int32_t s_grid_row_dsc[64 + 1];

void pui_lv_obj_set_grid(void *obj, int cols, int rows)
{
    if (cols > 64) cols = 64;
    if (rows > 64) rows = 64;
    for (int i = 0; i < cols; i++) s_grid_col_dsc[i] = LV_GRID_FR(1);
    s_grid_col_dsc[cols] = LV_GRID_TEMPLATE_LAST;
    for (int i = 0; i < rows; i++) s_grid_row_dsc[i] = LV_GRID_FR(1);
    s_grid_row_dsc[rows] = LV_GRID_TEMPLATE_LAST;
    lv_obj_set_grid_dsc_array((lv_obj_t *)obj, s_grid_col_dsc, s_grid_row_dsc);
}

void pui_lv_obj_set_grid_cell(void *obj, int col, int row, int colspan, int rowspan)
{
    lv_obj_set_grid_cell((lv_obj_t *)obj,
        LV_GRID_ALIGN_STRETCH, col, colspan,
        LV_GRID_ALIGN_STRETCH, row, rowspan);
}

/* ---- Style ---- */

void pui_lv_obj_set_style_bg_color(void *obj, uint32_t color)
{
    lv_obj_set_style_bg_color((lv_obj_t *)obj, lv_color_hex(color), 0);
    lv_obj_set_style_bg_opa((lv_obj_t *)obj, LV_OPA_COVER, 0);
}

void pui_lv_obj_set_style_bg_opa(void *obj, int opa)
{
    lv_obj_set_style_bg_opa((lv_obj_t *)obj, opa, 0);
}

void pui_lv_obj_set_style_text_color(void *obj, uint32_t color)
{
    lv_obj_set_style_text_color((lv_obj_t *)obj, lv_color_hex(color), 0);
}

void pui_lv_obj_set_style_text_font_size(void *obj, int size)
{
    /* Pick the closest built-in Montserrat font (pt → px at 96 dpi). */
    const int pixels = (size * 4 + 1) / 3;
    const lv_font_t *best = LV_FONT_DEFAULT;
    int distance = abs((int)best->line_height - pixels);

#define TRY_FONT(sz) do { \
    extern const lv_font_t lv_font_montserrat_##sz __attribute__((weak)); \
    if (&lv_font_montserrat_##sz && abs(sz - pixels) < distance) { \
        best = &lv_font_montserrat_##sz; distance = abs(sz - pixels); \
    } \
} while(0)

    TRY_FONT(8);  TRY_FONT(10); TRY_FONT(12); TRY_FONT(14);
    TRY_FONT(16); TRY_FONT(18); TRY_FONT(20); TRY_FONT(22);
    TRY_FONT(24); TRY_FONT(26); TRY_FONT(28); TRY_FONT(30);
    TRY_FONT(32); TRY_FONT(34); TRY_FONT(36); TRY_FONT(38);
    TRY_FONT(40); TRY_FONT(42); TRY_FONT(44); TRY_FONT(46);
    TRY_FONT(48);
#undef TRY_FONT

    lv_obj_set_style_text_font((lv_obj_t *)obj, best, 0);
}

void pui_lv_obj_set_style_pad_all(void *obj, int pad)
{
    lv_obj_set_style_pad_all((lv_obj_t *)obj, pad, 0);
}

void pui_lv_obj_set_style_pad(void *obj, int top, int right, int bottom, int left)
{
    lv_obj_t *o = (lv_obj_t *)obj;
    lv_obj_set_style_pad_top(o, top, 0);
    lv_obj_set_style_pad_right(o, right, 0);
    lv_obj_set_style_pad_bottom(o, bottom, 0);
    lv_obj_set_style_pad_left(o, left, 0);
}

void pui_lv_obj_set_style_pad_row(void *obj, int pad)
{
    lv_obj_set_style_pad_row((lv_obj_t *)obj, pad, 0);
}

void pui_lv_obj_set_style_pad_column(void *obj, int pad)
{
    lv_obj_set_style_pad_column((lv_obj_t *)obj, pad, 0);
}

void pui_lv_obj_set_style_border_width(void *obj, int w)
{
    lv_obj_set_style_border_width((lv_obj_t *)obj, w, 0);
}

void pui_lv_obj_set_style_radius(void *obj, int r)
{
    lv_obj_set_style_radius((lv_obj_t *)obj, r, 0);
}

void pui_lv_obj_set_style_margin(void *obj, int top, int right, int bottom, int left)
{
    lv_obj_t *o = (lv_obj_t *)obj;
    lv_obj_set_style_margin_top(o, top, 0);
    lv_obj_set_style_margin_right(o, right, 0);
    lv_obj_set_style_margin_bottom(o, bottom, 0);
    lv_obj_set_style_margin_left(o, left, 0);
}

void pui_lv_obj_set_transparent(void *obj)
{
    lv_obj_t *o = (lv_obj_t *)obj;
    lv_obj_set_style_bg_opa(o, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(o, 0, 0);
    lv_obj_set_style_radius(o, 0, 0);
}

/* ---- Visibility / state ---- */

void pui_lv_obj_set_hidden(void *obj, int hidden)
{
    if (hidden) lv_obj_add_flag((lv_obj_t *)obj, LV_OBJ_FLAG_HIDDEN);
    else        lv_obj_remove_flag((lv_obj_t *)obj, LV_OBJ_FLAG_HIDDEN);
}

void pui_lv_obj_set_clickable(void *obj, int clickable)
{
    if (clickable) lv_obj_add_flag((lv_obj_t *)obj, LV_OBJ_FLAG_CLICKABLE);
    else           lv_obj_remove_flag((lv_obj_t *)obj, LV_OBJ_FLAG_CLICKABLE);
}

void pui_lv_obj_set_scrollable(void *obj, int scrollable)
{
    if (scrollable) lv_obj_add_flag((lv_obj_t *)obj, LV_OBJ_FLAG_SCROLLABLE);
    else            lv_obj_remove_flag((lv_obj_t *)obj, LV_OBJ_FLAG_SCROLLABLE);
}

void pui_lv_obj_set_disabled(void *obj, int disabled)
{
    if (disabled) lv_obj_add_state((lv_obj_t *)obj, LV_STATE_DISABLED);
    else          lv_obj_remove_state((lv_obj_t *)obj, LV_STATE_DISABLED);
}

/* ---- Child ordering ---- */

void pui_lv_obj_move_to_index(void *obj, int index)
{
    lv_obj_move_to_index((lv_obj_t *)obj, index);
}

void pui_lv_obj_center(void *obj)
{
    lv_obj_center((lv_obj_t *)obj);
}

/* ---- Events ---- */

typedef struct {
    pui_event_cb_t cb;
    void          *user_data;
} pui_event_data_t;

static void event_dispatcher(lv_event_t *event)
{
    pui_event_data_t *data = (pui_event_data_t *)lv_event_get_user_data(event);
    lv_event_code_t code = lv_event_get_code(event);
    int pui_code = 0;
    switch (code) {
        case LV_EVENT_CLICKED:       pui_code = PUI_EVENT_CLICKED; break;
        case LV_EVENT_VALUE_CHANGED: pui_code = PUI_EVENT_VALUE_CHANGED; break;
        case LV_EVENT_READY:         pui_code = PUI_EVENT_READY; break;
        case LV_EVENT_DELETE:        pui_code = PUI_EVENT_DELETE; break;
        default: return;
    }
    data->cb(pui_code, data->user_data);
}

void *pui_lv_obj_add_event_cb(void *obj, pui_event_cb_t cb, void *user_data)
{
    pui_event_data_t *data = (pui_event_data_t *)malloc(sizeof(pui_event_data_t));
    data->cb = cb;
    data->user_data = user_data;
    lv_obj_add_event_cb((lv_obj_t *)obj, event_dispatcher, LV_EVENT_ALL, data);
    return data;
}

void pui_lv_obj_remove_event_cb(void *obj, void *descriptor)
{
    if (descriptor) {
        lv_obj_remove_event_cb_with_user_data((lv_obj_t *)obj, event_dispatcher, descriptor);
        free(descriptor);
    }
}

/* ---- Timer ---- */

typedef struct {
    void (*cb)(void *);
    void *user_data;
} pui_timer_data_t;

static void timer_dispatcher(lv_timer_t *timer)
{
    pui_timer_data_t *data = (pui_timer_data_t *)lv_timer_get_user_data(timer);
    data->cb(data->user_data);
}

void *pui_lv_timer_create(void (*cb)(void *), int period_ms, void *user_data)
{
    pui_timer_data_t *data = (pui_timer_data_t *)malloc(sizeof(pui_timer_data_t));
    data->cb = cb;
    data->user_data = user_data;
    return (void *)lv_timer_create(timer_dispatcher, period_ms, data);
}

void pui_lv_timer_delete(void *timer)
{
    if (timer) {
        pui_timer_data_t *data = (pui_timer_data_t *)lv_timer_get_user_data((lv_timer_t *)timer);
        lv_timer_delete((lv_timer_t *)timer);
        free(data);
    }
}

/* ---- Helpers ---- */

static char s_driver_name[32];

const char *pui_parse_driver_name(const char *config)
{
    pui_display_config_t cfg;
    parse_driver_config(config, &cfg);
    snprintf(s_driver_name, sizeof(s_driver_name), "%s", cfg.driver);
    return s_driver_name;
}
