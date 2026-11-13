"""Select the compiled LVGL extension for the requested display driver.

Each build is named after its drivers (liblvgl_sdl2, liblvgl_x11,
liblvgl_spi, ...). The driver comes from PUI_LVGL_DRIVER
("name#key=value#..."); PUI_LVGL_LIB names a build explicitly.
Every build also provides the "headless" driver.
"""
from __future__ import annotations
import importlib
import os
import re

_SPI_PANELS = {'ili9341', 'st7789'}
_PREFERENCE = ('sdl2', 'x11', 'spi')


def _builds():
    here = os.path.dirname(os.path.abspath(__file__))
    names = set()
    for filename in os.listdir(here):
        match = re.match(r'(liblvgl_[a-z0-9_]+)\.(?:.*\.)?(?:so|pyd|dylib)$', filename)
        if match:
            names.add(match.group(1))
    return names


def _drivers(build):
    tokens = set(build[len('liblvgl_'):].split('_'))
    supported = {'headless'} | tokens
    if 'spi' in tokens:
        supported |= _SPI_PANELS
    return tokens, supported


def _rank(build):
    tokens, _ = _drivers(build)
    return min((_PREFERENCE.index(t) for t in tokens if t in _PREFERENCE), default=len(_PREFERENCE)), build


def load():
    builds = _builds()
    explicit = os.environ.get('PUI_LVGL_LIB')
    if explicit:
        name = explicit if explicit.startswith('liblvgl_') else 'liblvgl_' + explicit
        candidates = [name]
    else:
        driver = os.environ.get('PUI_LVGL_DRIVER', '').split('#', 1)[0].strip().lower()
        candidates = sorted(builds, key=_rank)
        if driver:
            candidates = [b for b in candidates if driver in _drivers(b)[1]]
    if not candidates:
        raise ImportError(
            "No PUI.lvgl native extension for the requested driver "
            f"(found: {', '.join(sorted(builds)) or 'none'}). "
            "Build one with: make build_lvgl_sdl2 / make build_lvgl_x11")
    name = candidates[0]
    module = importlib.import_module('.' + name, __package__)
    tokens, supported = _drivers(name)
    default = next((t for t in _PREFERENCE if t in tokens), 'headless')
    if default == 'spi':
        default = 'ili9341'
    return module.ffi, module.lib, name, supported, default


ffi, lib, build, supported_drivers, default_driver = load()
