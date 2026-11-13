# Symbol fallbacks and bold Montserrat (ported from CPPUI's
# cmake/CPPUILVGLFonts.cmake). Patched copies of LVGL's Montserrat 14/28
# sources fall back to small symbol fonts (× · – →); bold variants fall back
# to the regular fonts. The LVGL checkout itself is never modified.
get_target_property(pui_font_sources lvgl SOURCES)
foreach(size 14 28)
    set(name "lv_font_montserrat_${size}.c")
    set(source "")
    foreach(candidate IN LISTS pui_font_sources)
        get_filename_component(candidate_name "${candidate}" NAME)
        if(candidate_name STREQUAL name)
            set(source "${candidate}")
        endif()
    endforeach()
    if(NOT source)
        message(FATAL_ERROR "Cannot find LVGL font source ${name}")
    endif()
    file(READ "${source}" code)
    string(FIND "${code}" ".fallback = NULL," position)
    if(position EQUAL -1)
        message(FATAL_ERROR "Font fallbacks expect LVGL 9.6; review ${name} before updating LVGL")
    endif()
    string(REPLACE ".fallback = NULL," ".fallback = &cppui_font_symbols_${size}," code "${code}")
    set(patched "${CMAKE_CURRENT_BINARY_DIR}/pui_${name}")
    file(WRITE "${patched}" "#include \"lvgl.h\"\nLV_FONT_DECLARE(cppui_font_symbols_${size})\n${code}")
    list(REMOVE_ITEM pui_font_sources "${source}")
    list(APPEND pui_font_sources "${patched}"
        "${CMAKE_CURRENT_SOURCE_DIR}/fonts/cppui_font_symbols_${size}.c"
        "${CMAKE_CURRENT_SOURCE_DIR}/fonts/cppui_font_montserrat_bold_${size}.c")
endforeach()
set_property(TARGET lvgl PROPERTY SOURCES "${pui_font_sources}")
target_compile_definitions(lvgl PUBLIC PUI_LVGL_BOLD_FONTS=1)
