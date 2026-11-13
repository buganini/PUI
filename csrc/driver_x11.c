#ifdef PUI_DRV_X11

#include <lvgl.h>
#include <X11/Xlib.h>
#include <time.h>
#include <stdio.h>

/* Supplied by the patched LVGL X11 driver (csrc/x11_driver_fixes.cmake). */
extern unsigned long pui_lvgl_x11_window_id(lv_display_t *disp);

static uint32_t x11_tick(void)
{
    static struct timespec start;
    static int started = 0;
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    if (!started) { start = now; started = 1; }
    return (uint32_t)((now.tv_sec - start.tv_sec) * 1000 + (now.tv_nsec - start.tv_nsec) / 1000000);
}

static void x11_delay(uint32_t ms)
{
    struct timespec ts = { ms / 1000, (long)(ms % 1000) * 1000000L };
    nanosleep(&ts, NULL);
}

lv_display_t *pui_drv_x11_init(int w, int h, const char *title)
{
    /* LVGL 9.6's X11 driver assumes XOpenDisplay succeeds. */
    Display *probe = XOpenDisplay(NULL);
    if (!probe) {
        fprintf(stderr, "pui_lvgl: cannot open the X11 display; set DISPLAY to an available X server\n");
        return NULL;
    }
    XCloseDisplay(probe);
    lv_tick_set_cb(x11_tick);
    lv_delay_set_cb(x11_delay);
    lv_display_t *disp = lv_x11_window_create(title, w, h);
    if (!disp) return NULL;
    /* Creates the pointer, wheel and keyboard devices and the default group. */
    lv_x11_inputs_create(disp, NULL);
    return disp;
}

void pui_drv_x11_set_title(lv_display_t *disp, const char *title)
{
    _x11_user_hdr_t *hdr = (_x11_user_hdr_t *)lv_display_get_driver_data(disp);
    XStoreName(hdr->display, pui_lvgl_x11_window_id(disp), title);
    XFlush(hdr->display);
}

void pui_drv_x11_set_size(lv_display_t *disp, int w, int h)
{
    /* SDL resizes its window on LV_EVENT_RESOLUTION_CHANGED; the X11 driver
       only reallocates its draw buffers, so resize the host window here. */
    _x11_user_hdr_t *hdr = (_x11_user_hdr_t *)lv_display_get_driver_data(disp);
    XResizeWindow(hdr->display, pui_lvgl_x11_window_id(disp), w, h);
    XFlush(hdr->display);
    lv_display_set_resolution(disp, w, h);
}

void pui_drv_x11_deinit(void)
{
    /* lv_deinit deletes the display; the patched driver joins its tick thread. */
}

#endif /* PUI_DRV_X11 */
