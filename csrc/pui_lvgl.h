#ifndef PUI_LVGL_H
#define PUI_LVGL_H

/* Display/driver bring-up only. Widgets are driven from Python through
   cffi declarations of the LVGL API itself (see PUI/lvgl/build_lvgl_cffi.py). */

#include <stdint.h>
#include <lvgl.h>

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


/* Parse "driver#key=val#..." and bring up the display.
   Drivers: headless (always), sdl2, x11, ili9341/st7789 (SPI).
   Returns 0 on success, -1 on error. */
int  pui_lvgl_init(const char *driver_config);
void pui_lvgl_deinit(void);

/* Run one LVGL timer tick; returns ms until next call is useful. */
uint32_t pui_lvgl_timer_handler(void);

/* Non-zero while the display is still alive. */
int pui_lvgl_is_running(void);

/* Desktop window title / resolution (no-op on fixed panels). */
void pui_lvgl_set_title(const char *title);
void pui_lvgl_set_size(int w, int h);

/* Parse "driver#k=v#..." — exposed so Python tests can validate format. */
const char *pui_parse_driver_name(const char *config);

#endif /* PUI_LVGL_H */
