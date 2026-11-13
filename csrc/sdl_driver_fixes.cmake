# Corrections to LVGL v9.6.0's SDL driver. A patched copy is compiled instead
# of the original; the LVGL checkout itself is never modified.
#  - On SDL_QUIT (sent after the last window closes) the stock driver calls
#    SDL_Quit() and lv_deinit() from inside lv_timer_handler (and exit(0) with
#    LV_SDL_DIRECT_EXIT). The window-close event has already deleted the
#    display, so let the application's main loop end and shut down in order
#    (inputs, display, lv_sdl_quit(), lv_deinit()), as CPPUI's runtime does.
set(sdl_source "${PUI_LVGL_SOURCE_DIR}/src/drivers/sdl/lv_sdl_window.c")
file(READ "${sdl_source}" sdl_code)
set(quit_site "        if(event.type == SDL_QUIT) {\n            SDL_Quit();\n            lv_deinit();\n            inited = false;\n")
string(FIND "${sdl_code}" "${quit_site}" position)
if(position EQUAL -1)
    message(FATAL_ERROR "SDL driver fixes expect LVGL v9.6.0; review the driver before updating LVGL")
endif()
string(REPLACE "${quit_site}" "        if(event.type == SDL_QUIT) {\n" sdl_code "${sdl_code}")
set(patched_sdl "${CMAKE_CURRENT_BINARY_DIR}/lv_sdl_window.c")
file(WRITE "${patched_sdl}" "${sdl_code}")
get_target_property(lvgl_sources lvgl SOURCES)
list(REMOVE_ITEM lvgl_sources "${sdl_source}")
list(APPEND lvgl_sources "${patched_sdl}")
set_property(TARGET lvgl PROPERTY SOURCES "${lvgl_sources}")
target_include_directories(lvgl PRIVATE "${PUI_LVGL_SOURCE_DIR}/src/drivers/sdl")
