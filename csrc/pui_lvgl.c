#include "pui_lvgl.h"
#include <lvgl.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

/* ---- Driver config parsing (same logic as alarm's parse_driver_profile) ---- */


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
extern lv_display_t *pui_drv_sdl2_init(int w, int h, const char *title, lv_group_t **group);
extern void pui_drv_sdl2_deinit(void);
#endif
#ifdef PUI_DRV_X11
extern lv_display_t *pui_drv_x11_init(int w, int h, const char *title);
extern void pui_drv_x11_deinit(void);
extern void pui_drv_x11_set_title(lv_display_t *disp, const char *title);
extern void pui_drv_x11_set_size(lv_display_t *disp, int w, int h);
extern int pui_drv_x11_alive(void);
#endif
#ifdef PUI_DRV_SPI
extern lv_display_t *pui_drv_spi_init(const pui_display_config_t *cfg);
extern void pui_drv_spi_deinit(void);
#endif

/* ---- Headless driver (always available; used for tests and snapshots) ---- */

#include <time.h>

static void *s_headless_buf = NULL;

static uint32_t headless_tick(void)
{
    static struct timespec start;
    static int started = 0;
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    if (!started) { start = now; started = 1; }
    return (uint32_t)((now.tv_sec - start.tv_sec) * 1000 + (now.tv_nsec - start.tv_nsec) / 1000000);
}

static void headless_flush(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map)
{
    (void)area; (void)px_map;
    lv_display_flush_ready(disp);
}

static lv_display_t *headless_init(int w, int h)
{
    lv_tick_set_cb(headless_tick);
    lv_display_t *disp = lv_display_create(w, h);
    if (!disp) return NULL;
    size_t size = (size_t)w * 40 * 4;
    s_headless_buf = malloc(size);
    lv_display_set_buffers(disp, s_headless_buf, NULL, size, LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(disp, headless_flush);
    return disp;
}

/* ---- Init / deinit (mirrors CPPUI's LVGL::Runtime) ---- */

#define PUI_MAX_INPUTS 8

static lv_indev_t *s_inputs[PUI_MAX_INPUTS];   /* devices created by our driver */
static int s_input_count = 0;
static lv_group_t *s_group = NULL;             /* group we created, if any */
static lv_group_t *s_previous_group = NULL;

static void display_deleted(lv_event_t *e)
{
    /* The window was closed (or the display deleted by its driver). */
    (void)e;
    s_display = NULL;
}

static void input_deleted(lv_event_t *e)
{
    lv_indev_t *input = (lv_indev_t *)lv_event_get_target(e);
    for (int i = 0; i < s_input_count; i++) {
        if (s_inputs[i] == input) {
            s_inputs[i] = s_inputs[--s_input_count];
            break;
        }
    }
}

static int is_known_input(lv_indev_t *input, lv_indev_t **known, int count)
{
    for (int i = 0; i < count; i++)
        if (known[i] == input) return 1;
    return 0;
}

int pui_lvgl_init(const char *driver_config, const char *title)
{
    if (s_running) return 0;
    if (!title) title = "";

    if (parse_driver_config(driver_config, &s_config) != 0)
        return -1;

    lv_init();

    /* Remember existing input devices; the driver's new ones are ours to delete. */
    lv_indev_t *previous[PUI_MAX_INPUTS];
    int previous_count = 0;
    for (lv_indev_t *i = lv_indev_get_next(NULL); i && previous_count < PUI_MAX_INPUTS; i = lv_indev_get_next(i))
        previous[previous_count++] = i;
    s_previous_group = lv_group_get_default();
    s_group = NULL;

    lv_display_t *disp = NULL;
    if (strcmp(s_config.driver, "headless") == 0) {
        disp = headless_init(s_config.width, s_config.height);
        if (disp) {
            s_group = lv_group_create();
            lv_group_set_default(s_group);
        }
    }
#ifdef PUI_DRV_SDL2
    if (strcmp(s_config.driver, "sdl2") == 0) {
        disp = pui_drv_sdl2_init(s_config.width, s_config.height, title, &s_group);
    }
#endif
#ifdef PUI_DRV_X11
    if (strcmp(s_config.driver, "x11") == 0)
        disp = pui_drv_x11_init(s_config.width, s_config.height, title);
#endif
#ifdef PUI_DRV_SPI
    if (strcmp(s_config.driver, "ili9341") == 0 || strcmp(s_config.driver, "st7789") == 0)
        disp = pui_drv_spi_init(&s_config);
#endif

    s_input_count = 0;
    for (lv_indev_t *i = lv_indev_get_next(NULL); i; i = lv_indev_get_next(i)) {
        if (is_known_input(i, previous, previous_count) || s_input_count >= PUI_MAX_INPUTS) continue;
        s_inputs[s_input_count++] = i;
        lv_indev_add_event_cb(i, input_deleted, LV_EVENT_DELETE, NULL);
    }

    if (!disp) {
        fprintf(stderr, "pui_lvgl: unsupported or unavailable driver '%s'\n", s_config.driver);
        s_running = 1;
        pui_lvgl_deinit();
        return -1;
    }
    s_display = disp;
    lv_display_add_event_cb(disp, display_deleted, LV_EVENT_DELETE, NULL);
    s_running = 1;
    return 0;
}

void pui_lvgl_deinit(void)
{
    if (!s_running) return;
    s_running = 0;
    if (lv_is_initialized()) {
        /* Input callbacks can refer to display driver data until deleted. */
        while (s_input_count > 0) {
            lv_indev_t *input = s_inputs[--s_input_count];
            lv_indev_remove_event_cb_with_user_data(input, input_deleted, NULL);
            lv_indev_delete(input);
        }
        if (s_display) {
            lv_display_remove_event_cb_with_user_data(s_display, display_deleted, NULL);
            lv_display_delete(s_display);
            s_display = NULL;
        }
        if (s_group) {
            lv_group_delete(s_group);
            lv_group_set_default(s_previous_group);
        }
    }
    s_display = NULL;
    s_group = s_previous_group = NULL;
    s_input_count = 0;
    if (strcmp(s_config.driver, "headless") == 0) {
        free(s_headless_buf);
        s_headless_buf = NULL;
    }
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
    /* SDL's own SDL_QUIT handling may already have deinitialized LVGL. */
    if (lv_is_initialized()) lv_deinit();
}

uint32_t pui_lvgl_timer_handler(void)
{
    if (!s_running) return 100;
    return lv_timer_handler();
}

int pui_lvgl_is_running(void)
{
    if (!s_running || !lv_is_initialized()) return 0;
#ifdef PUI_DRV_X11
    if (strcmp(s_config.driver, "x11") == 0 && !pui_drv_x11_alive()) return 0;
#endif
    return s_running && lv_display_get_next(NULL) != NULL;
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


/* ==== Extended API ==== */

/* ---- Display ---- */

void pui_lvgl_set_title(const char *title)
{
    if (!s_display || !lv_display_get_next(NULL)) return;
#if defined(PUI_DRV_SDL2) && LV_USE_SDL
    if (strcmp(s_config.driver, "sdl2") == 0)
        lv_sdl_window_set_title(s_display, title);
#endif
#if defined(PUI_DRV_X11) && LV_USE_X11
    if (strcmp(s_config.driver, "x11") == 0)
        pui_drv_x11_set_title(s_display, title);
#endif
    (void)title;
}

void pui_lvgl_set_size(int w, int h)
{
    if (!s_display || w <= 0 || h <= 0) return;
    if (lv_display_get_horizontal_resolution(s_display) == w &&
        lv_display_get_vertical_resolution(s_display) == h) return;
    /* Embedded panels have a fixed resolution. */
#if defined(PUI_DRV_X11) && LV_USE_X11
    if (strcmp(s_config.driver, "x11") == 0) {
        pui_drv_x11_set_size(s_display, w, h);
        return;
    }
#endif
    if (strcmp(s_config.driver, "sdl2") != 0 && strcmp(s_config.driver, "headless") != 0) return;
    if (strcmp(s_config.driver, "headless") == 0) {
        free(s_headless_buf);
        size_t size = (size_t)w * 40 * 4;
        s_headless_buf = malloc(size);
        lv_display_set_buffers(s_display, s_headless_buf, NULL, size, LV_DISPLAY_RENDER_MODE_PARTIAL);
    }
    lv_display_set_resolution(s_display, w, h);
}

