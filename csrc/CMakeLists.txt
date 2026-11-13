cmake_minimum_required(VERSION 3.13)
cmake_policy(SET CMP0079 NEW)
project(pui_lvgl LANGUAGES C)

# LVGL renders in software; an unoptimized (-O0) build is several times slower.
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(PUI_LVGL_SOURCE_DIR "" CACHE PATH "LVGL v9.6.0 source checkout")
if(NOT EXISTS "${PUI_LVGL_SOURCE_DIR}/lvgl.h")
    message(FATAL_ERROR "Set PUI_LVGL_SOURCE_DIR to an LVGL 9.6.0 source checkout")
endif()

set(LV_BUILD_CONF_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lv_conf.h" CACHE PATH "" FORCE)
set(CONFIG_LV_BUILD_DEMOS OFF CACHE BOOL "" FORCE)
set(CONFIG_LV_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(CONFIG_LV_USE_THORVG_INTERNAL OFF CACHE BOOL "" FORCE)
set(LV_FETCH_DEPENDENCIES OFF CACHE BOOL "" FORCE)

option(PUI_DRV_SDL2 "Enable SDL2 display driver" OFF)
option(PUI_DRV_X11 "Enable X11 display driver" OFF)
option(PUI_DRV_SPI "Enable SPI display driver" OFF)

add_subdirectory("${PUI_LVGL_SOURCE_DIR}" "${CMAKE_CURRENT_BINARY_DIR}/lvgl")

target_compile_definitions(lvgl PUBLIC
    PUI_DRV_SDL2=$<BOOL:${PUI_DRV_SDL2}>
    PUI_DRV_X11=$<BOOL:${PUI_DRV_X11}>
    PUI_DRV_SPI=$<BOOL:${PUI_DRV_SPI}>)

if(PUI_DRV_SDL2)
    find_package(SDL2 REQUIRED)
    target_link_libraries(lvgl PUBLIC SDL2::SDL2)
endif()

if(PUI_DRV_X11)
    find_package(X11 REQUIRED)
    find_package(Threads REQUIRED)
    target_link_libraries(lvgl PUBLIC X11::X11 Threads::Threads)
    include("${CMAKE_CURRENT_SOURCE_DIR}/x11_driver_fixes.cmake")
endif()

include("${CMAKE_CURRENT_SOURCE_DIR}/fonts.cmake")

if(UNIX)
    target_link_libraries(lvgl PUBLIC m)
endif()
