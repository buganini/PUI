# LVGL alignment progress

**Missing** means no implementation; **Partial** means a known functional gap.
Completed changes belong in the reference and changelog.

The backend drives LVGL 9.6 through cffi declarations of the LVGL API; C code is
limited to display/driver bring-up (`csrc/`). Builds are per driver
(`liblvgl_sdl2`, `liblvgl_x11`, `liblvgl_spi`). Checks: `make lvgl_test` runs
headless cookbook interactions, open/close in real SDL2 and X11 windows (X11 on a
private Xvfb) and page snapshots.

## Missing or incomplete behavior

| Priority | Area | State | Remaining work |
| --- | --- | --- | --- |
| P1 | SPI LCD driver (ILI9341/ST7789) | WIP | `csrc/driver_spi.c` is an unvalidated skeleton: never compiled or run on hardware. Known problems: whole-area SPI transfers exceed spidev's default 4096-byte limit; RGB565 is not byte-swapped for the panel; GPIO uses deprecated sysfs (fails with offset GPIO numbering on current kernels); `rotate`/`flip_x`/`flip_y`/`color_invert`/offsets are not applied (no MADCTL/window offsets) and `baudrate` is ignored; minimal init sequences; no touch or keypad input |
| P1 | Window keyboard/icon | Missing | `.keypress` forwarding, the icon option, and maximize/fullscreen (single display; currently no-ops) |
| P1 | AI supervision | Missing | `ai/native.py` has no LVGL command poster; `app.start(codex=...)` / `claude=` is unsupported |
| P1 | Canvas path clipping | Missing | `clipPath` (`supports_path_clip = False`); rectangle clipping works. Matplotlib circle clips are therefore not applied |
| P1 | Canvas wheel on X11 | Missing | X11 reports the wheel as a separate encoder device; only SDL2 delivers `.wheel` to Canvas |
| P2 | Fonts | Partial | Only bundled Montserrat: regular 8–48 px, bold and the `× · – →` symbol fallbacks at 14 and 28 px only. Other glyphs (e.g. `…`) render as boxes; `fontFamily` cannot select other faces |
| P2 | Selectable text | Missing | Label/Text `selectable` is ignored |
| P2 | Modal | Partial | Escape does not dismiss; the modal covers the single display window |
| P2 | Canvas HiDPI | Partial | `pixel_density` is fixed at 1.0 |
| P2 | Table | Partial | Headers are ordinary first row/column cells (no header styling); no cell widgets, sorting or keyboard cell editing |
| P2 | Tree | Partial | Pointer only; no keyboard navigation |
| P3 | HTML/Markdown | Missing | Classes display plain text (`pui_supported=False`) |
| P3 | Toolbars/MDI/interop | Missing | ToolBar, MDI and NativeWidget/WidgetWrapper |
| Shared | Drag/drop | Missing | Inbound files/text/URLs |
| Shared | Layout overflow | Partial | LVGL does not propagate content minimums through percentage-sized parents; a parent forced narrower than its content clips instead of growing (see Scroll notes in Layout) |
