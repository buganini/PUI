#ifdef PUI_DRV_SDL2

#include <lvgl.h>
#include <stdint.h>

#include <stdio.h>

/* Mirrors CPPUI's LVGL::Runtime for SDL2. */
lv_display_t *pui_drv_sdl2_init(int w, int h, const char *title, lv_group_t **group_out)
{
    lv_display_t *disp = lv_sdl_window_create(w, h);
    if (!disp || !lv_sdl_window_get_renderer(disp)) {
        fprintf(stderr, "pui_lvgl: failed to initialize the SDL display\n");
        if (disp) lv_display_delete(disp);
        return NULL;
    }
    /* LVGL follows SDL_WINDOWEVENT_RESIZED; the window just has to allow it. */
    lv_sdl_window_set_resizeable(disp, true);
    if (title && *title) lv_sdl_window_set_title(disp, title);

    lv_indev_t *pointer  = lv_sdl_mouse_create();
    lv_indev_t *keyboard = lv_sdl_keyboard_create();
    if (!pointer || !keyboard) {
        fprintf(stderr, "pui_lvgl: failed to initialize SDL input devices\n");
        return disp;
    }
    lv_group_t *group = lv_group_create();
    lv_group_set_default(group);
    lv_indev_set_group(pointer, group);
    lv_indev_set_group(keyboard, group);
    *group_out = group;
    return disp;
}

void pui_drv_sdl2_deinit(void)
{
    /* Release SDL once no LVGL display uses it (CPPUI does the same). */
    if (lv_is_initialized() && !lv_display_get_next(NULL)) lv_sdl_quit();
}

#endif /* PUI_DRV_SDL2 */
