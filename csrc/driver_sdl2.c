#ifdef PUI_DRV_SDL2

#include <lvgl.h>
#include <stdint.h>

lv_display_t *pui_drv_sdl2_init(int w, int h)
{
    lv_display_t *disp = lv_sdl_window_create(w, h);
    if (!disp) return NULL;

    lv_group_t *group = lv_group_create();
    lv_group_set_default(group);

    lv_indev_t *mouse = lv_sdl_mouse_create();
    lv_indev_t *kb    = lv_sdl_keyboard_create();
    if (mouse) lv_indev_set_group(mouse, group);
    if (kb)    lv_indev_set_group(kb, group);

    return disp;
}

void pui_drv_sdl2_deinit(void)
{
    /* SDL cleanup is handled by lv_deinit / atexit. */
}

#endif /* PUI_DRV_SDL2 */
