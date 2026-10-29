# tkinter alignment progress

Latest runtime audit: [2026-10-28 macOS validation](validation-2026-10-28.md).

Autocomplete follows the [shared acceptance criteria](https://buganini.github.io/PUI/doc/Reference.html#autocomplete-acceptance).

**Missing** means no implementation; **Partial** means a known functional gap.
Completed changes belong in the reference and changelog.

Implemented integrations are **complete**. This backlog tracks missing functionality,
known bugs and design decisions. Additional test coverage does not keep a feature
open. Detailed test environments, results and follow-up QA are in
[validation notes](validation-2026-10-30.md#tkinter). Platform names below identify
known differences or specific bugs, not a mandatory three-OS completion matrix.

## Missing or incomplete behavior

| Priority | Area | State | Remaining work |
| --- | --- | --- | --- |
| P2 | TextField/MaskedField placeholder | Partial | Accepts placeholder=None but displays no hint on Tk 8.6 Entry. The user chose to defer emulation; preserve real entry/model values and revisit only with an approved design or supported native API |
| P1 | Canvas events | Missing | Wire `.mousedown`, `.mouseup`, `.mousemove`, `.mouseenter`, `.mouseleave`, `.dblclick`, and `.wheel`, including coordinates/buttons/modifiers |
| P1 | Canvas sizing/repaint | Partial | Honor the painter's immediate-redraw return value; allocated dimensions and native resize repaint are implemented |
| P1 | Window keyboard/icon | Missing | Implement `.keypress` forwarding and the common icon option |
| P1 | Layout dimensions | Partial | Native text dimensions round pixel requests up to whole characters/lines. Axes without native sizing options remain unsupported |
| P1 | Selectable text | Missing | Honor Label/Text `selectable`; both currently use ordinary tk.Label widgets |
| P2 | Canvas curves/geometry | Missing | Implement `drawCubicBezier` and `drawShapely`; agree a renderer/approximation and optional dependencies first |
| P2 | Canvas file images | Partial | RGBA memory drawImage, crop, resize and opacity are implemented with Pillow. Add file ImageResource/loadImage APIs |
| P2 | Canvas text/HiDPI | Partial | Implement text height clipping, align width clipping with the Canvas Functions contract, and report actual display density instead of the fixed 1.0 fallback |
| P2 | Image | Missing | Implement the standalone Image control; agree formats/scaling before adding dependencies |
| P2 | Table advanced interaction | Missing | Cell widgets, drag/drop or header sorting, per-cell styles, and cell-cursor parity; Treeview provides row selection. Agree any additions before implementing custom renderers or overlays |
| P3 | HTML/Markdown | Missing | Choose native support or approve dependencies; current classes display plain text |
| P3 | Toolbars/MDI/interop | Missing | Define supported desktop scope and native ownership before implementation |
| P3 | Matplotlib navigation toolbar | Missing | FigureCanvasTkAgg rendering and native events are implemented; PUI navigation controls remain pending |
| Shared | Drag/drop | Missing | Implement the established inbound files/text/URLs contract using suitable native integration; outgoing drags remain a separate design |

Canvas callback registration is inherited from PUINode, but Canvas and
TkBaseWidget do not bind these input events. Existing shape drawing tests do
not establish pointer-event support. The HeavyCanvas cookbook consequently
has no hover crosshair/tooltip or wheel zoom on Tk.

## Known issues

The macOS Tk 9.1 run had two fullscreen-exit assertion failures and a ComboBox
test failure caused by its hard-coded `.popdown.f.l` widget path. They also occur
with the committed Window implementation; investigate these separately from
completed menu and Tree integration. See the validation notes for the run.

## Decisions to discuss

- Layout: decide whether unsupported axes or exact sub-character/line dimensions need wrappers; current conversion preserves native widgets.
- Canvas: agree cubic rendering and text bounds/anchors; smooth Tk lines do not
  establish compatibility with the common cubic API.
- File images, HTML/Markdown and geometry: approve dependencies or define
  a limited native contract; avoid custom parsers/resamplers.
- Advanced Table interaction and desktop components: agree native composition,
  editing, ownership, and feature scope.
- Inbound drag/drop: follow the [shared payload/lifecycle contract](https://buganini.github.io/PUI/doc/Reference.html#drop); native Tk integration remains missing.
- Canvas contract questions: see [wx-progress.md](wx-progress.md).

## Baseline and process

Use backend `Application`/`PUIView` classes for new code and examples. Keep
deprecated decorators covered by compatibility checks during migration.

Use the current [common reference](https://buganini.github.io/PUI/doc/Reference.html)
and [layout policy](https://buganini.github.io/PUI/doc/Layout.html) as the shared
contract. Historical porting baselines remain in Git history; they must not
reintroduce superseded priorities, sizing or lifecycle behavior.
For Window state, follow the current [initial-only declaration contract](https://buganini.github.io/PUI/doc/Reference.html#window)
instead of the imperative methods introduced in `95e6cff`.

Work through remaining priorities; skip decisions requiring user input and
continue independent items. Preserve native geometry/ownership. Update this
document, relevant references, and Changelog.txt after each change; validate and
commit each completed change. Remove finished rows, retain known functional gaps, and
avoid temporary artifact paths.
See [README](../README.md) for installation and [common reference](https://buganini.github.io/PUI/doc/Reference.html)
for implemented behavior.

## Canvas / Matplotlib functional gaps

MatplotlibCanvas embeds FigureCanvasTkAgg, retaining native rendering, text,
path clipping and input events. Figure/canvas survive reconciliation; pending
Tk idle draws and event-loop callbacks are cancelled on removal. A PUI navigation
toolbar is still pending.

The ordinary PUI Canvas still supports M/L/Z path strokes and RGBA images;
its clipping remains a no-op and compound filled paths remain unsupported.
