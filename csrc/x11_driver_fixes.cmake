# Corrections to LVGL v9.6.0's X11 display driver (ported from CPPUI's
# cmake/CPPUILVGLX11.cmake). A patched copy is compiled instead of the
# original; the LVGL checkout itself is never modified.
#  - Show a native arrow cursor. The stock driver hides the pointer and LVGL
#    draws none, so the mouse is invisible over the window.
#  - Join the tick thread when the display is deleted (lv_display_delete /
#    lv_deinit), not only on a window-manager close; otherwise the thread can
#    touch freed driver data after shutdown.
#  - Make the shared stop flag atomic.
#  - Expose: repaint every exposed rectangle at its own position. The stock
#    driver repaints only the last one, from (0,0) with its size, so a first
#    frame flushed before the window was mapped could stay mostly blank.
#  - Export the native Window id so PUI can set the title and resize it.
set(x11_source "${PUI_LVGL_SOURCE_DIR}/src/drivers/x11/lv_x11_display.c")
file(READ "${x11_source}" x11_code)
set(delete_site "    x11_disp_data_t * xd = lv_display_get_driver_data(disp);\n\n    lv_timer_delete(xd->timer);")
set(close_site "                    xd->terminated = true;\n                    void * ret = NULL;\n                    pthread_join(xd->thr_tick, &ret);\n")
set(cursor_site [=[    XColor black = { .red = 0, .green = 0, .blue = 0 };
    char empty_data[] = { 0 };

    Pixmap empty_bitmap = XCreateBitmapFromData(xd->hdr.display, xd->window, empty_data, 1, 1);
    Cursor inv_cursor = XCreatePixmapCursor(xd->hdr.display, empty_bitmap, empty_bitmap, &black, &black, 0, 0);
    XDefineCursor(xd->hdr.display, xd->window, inv_cursor);
    XFreeCursor(xd->hdr.display, inv_cursor);
    XFreePixmap(xd->hdr.display, empty_bitmap);]=])
set(expose_site [=[                if(event.xexpose.count == 0) {
                    XPutImage(xd->hdr.display, xd->window, xd->gc, xd->ximage, 0, 0, 0, 0, event.xexpose.width, event.xexpose.height);
                }]=])
foreach(fragment IN ITEMS "${delete_site}" "${close_site}" "${cursor_site}" "${expose_site}" "x11_hide_cursor" "bool            terminated;")
    string(FIND "${x11_code}" "${fragment}" position)
    if(position EQUAL -1)
        message(FATAL_ERROR "X11 driver fixes expect LVGL v9.6.0; review the driver before updating LVGL")
    endif()
endforeach()
string(REPLACE "${delete_site}"
    "    x11_disp_data_t * xd = lv_display_get_driver_data(disp);\n\n    xd->terminated = true;\n    pthread_join(xd->thr_tick, NULL);\n    lv_timer_delete(xd->timer);"
    x11_code "${x11_code}")
string(REPLACE "${close_site}" "" x11_code "${x11_code}")
string(REPLACE "bool            terminated;" "_Atomic bool    terminated;" x11_code "${x11_code}")
string(REPLACE "${cursor_site}"
    "    Cursor cursor = XCreateFontCursor(xd->hdr.display, XC_left_ptr);\n    XDefineCursor(xd->hdr.display, xd->window, cursor);\n    XFreeCursor(xd->hdr.display, cursor);"
    x11_code "${x11_code}")
string(REPLACE "x11_hide_cursor" "x11_set_cursor" x11_code "${x11_code}")
string(REPLACE "${expose_site}"
    "                XPutImage(xd->hdr.display, xd->window, xd->gc, xd->ximage, event.xexpose.x, event.xexpose.y,\n                          event.xexpose.x, event.xexpose.y, event.xexpose.width, event.xexpose.height);"
    x11_code "${x11_code}")
string(APPEND x11_code "\n#if LV_USE_X11\nunsigned long pui_lvgl_x11_window_id(lv_display_t * disp) {\n    x11_disp_data_t * xd = lv_display_get_driver_data(disp);\n    return xd->window;\n}\n#endif\n")
set(patched_x11 "${CMAKE_CURRENT_BINARY_DIR}/lv_x11_display.c")
file(WRITE "${patched_x11}" "#include <stdatomic.h>\n#include <X11/cursorfont.h>\n${x11_code}")
get_target_property(lvgl_sources lvgl SOURCES)
list(REMOVE_ITEM lvgl_sources "${x11_source}")
list(APPEND lvgl_sources "${patched_x11}")
set_property(TARGET lvgl PROPERTY SOURCES "${lvgl_sources}")
target_compile_features(lvgl PRIVATE c_std_11)
target_include_directories(lvgl PRIVATE "${PUI_LVGL_SOURCE_DIR}/src/drivers/x11")
