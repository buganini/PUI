# tkinter alignment progress

Autocomplete validation must follow the [shared acceptance criteria](Reference.html#autocomplete-acceptance); unverified cases remain pending, including real IME and platform-specific focus behavior.

Only unfinished work is listed below. **Missing** means the named behavior has
no implementation; **Partial** means an implementation exists but the listed gap
remains; **Unverified** means code exists but the stated runtime check is pending.
Completed changes belong in the changelog and reference, not the backlog.

## Missing or incomplete behavior

| Priority | Area | State | Remaining work |
| --- | --- | --- | --- |
| P2 | TextField/MaskedField placeholder | Partial | Accepts placeholder=None but displays no hint on Tk 8.6 Entry. The user chose to defer emulation; preserve real entry/model values and revisit only with an approved design or supported native API |
| P1 | Canvas events | Missing | Wire `.mousedown`, `.mouseup`, `.mousemove`, `.mouseenter`, `.mouseleave`, `.dblclick`, and `.wheel`, including coordinates/buttons/modifiers |
| P1 | Canvas sizing/repaint | Partial | Honor the painter's immediate-redraw return value; allocated dimensions and native resize repaint are implemented |
| P1 | Window keyboard/icon | Missing | Implement `.keypress` forwarding and the common icon option |
| P1 | Linear alignment | Unverified | HBox/VBox use sibling-local main-axis priorities and vertically center compact HBox children and left-align compact VBox children. Broaden platform checks for explicit dimensions and native size limits |
| P1 | Layout dimensions | Partial | Resolve pixel dimensions versus Tk text character/line units and wrapper sizing |
| P1 | Selectable text | Missing | Honor Label/Text `selectable`; both currently use ordinary tk.Label widgets |
| P2 | Canvas curves/geometry | Missing | Implement `drawCubicBezier` and `drawShapely`; agree a renderer/approximation and optional dependencies first |
| P2 | Canvas images | Missing | Implement ImageResource/loadImage/drawImage with agreed format, crop, scale, and opacity support |
| P2 | Canvas text/HiDPI | Partial | Implement text height clipping, resolve shared bounds/anchors, and report actual display density instead of the fixed 1.0 fallback |
| P2 | Image | Missing | Implement the standalone Image control; agree formats/scaling before adding dependencies |
| P2 | ComboBox autocomplete | Partial | Independent suggestions retain editor focus on Linux. Validate real IME composition, macOS/Windows, theme/DPI, parent scrolling and window movement. The ordinary ttk arrow dropdown retains native focus behavior. |
| P2 | Splitter/Modal | Missing | Choose native composition and lifecycle, then implement reconciliation |
| P2 | Stack | Unverified | Frame/grid/lift implemented; macOS/Windows focus, hit testing and theme checks remain. Linux geometry, stacking order, resize and keyed reconciliation are tested |
| P2 | Tree | Missing | Agree native data views, editing, and selection/expansion preservation |
| P2 | Table advanced interaction | Missing | Cell widgets, drag/drop or header sorting, per-cell styles, and cell-cursor parity; Treeview provides row selection. Agree any additions before implementing custom renderers or overlays |
| P3 | HTML/Markdown | Missing | Choose native support or approve dependencies; current classes display plain text |
| P3 | Menus/toolbars/MDI/interop | Missing | Define supported desktop scope and native ownership before implementation |
| P3 | MatplotlibCanvas | Missing | Agree integration and approve the optional dependency |
| Shared | Drag/drop | Missing | Define common payload/lifecycle semantics before implementation |

Canvas callback registration is inherited from PUINode, but Canvas and
TkBaseWidget do not bind these input events. Existing shape drawing tests do
not establish pointer-event support. The HeavyCanvas cookbook consequently
has no hover crosshair/tooltip or wheel zoom on Tk.

## Validation still needed

| Area | State | Pending check |
| --- | --- | --- |
| Disabled controls | Unverified | Broader mouse/keyboard focus and platform behavior; tests/tkinter_regression.py covers Button/Checkbox/RadioButton activation blocking and ComboBox value/editability retention through disabled toggles |
| Views | Unverified | Manual focus/keyboard transitions and other platforms; selection, retained edits, keyed moves/removal and model replacement are covered by tests/tkinter_views.py |
| Tabs models | Unverified | Broader keyboard/focus and platform behavior; native selection events, optional models, duplicate keys, keyed moves, labels and empty transitions are covered by tests/tkinter_tabs.py |
| Scroll | Unverified | Exercise resize, END following, content growth, user-position preservation, and local wheel behavior |
| Dialogs | Unverified | Operate native dialogs; current helper tests check argument/result conversion |
| Table | Unverified | Manual keyboard/focus, column resizing/scrolling, display scaling, other platforms and large-data performance. tests/tkinter_table.py covers native rows, typed dialog edits/choices, callbacks, redraws, keyed moves, delayed dialog visibility, cancellation before display and teardown |
| Window | Unverified | Broaden native state/close checks on other window managers/platforms and multi-window modal focus. tests/tkinter_lifecycle.py covers last-window exit, retained other windows, replacement/removal, and dialog/timer/redraw cleanup |
| Layout/Tabs | Unverified | Compare geometry, resizing, and ttk tab placement with PySide6 |
| Canvas | Unverified | Broaden font/theme repaint and performance checks to macOS/Windows; measure item recreation and memory use with the native 120,000–1,000,000-session presets; tests/tkinter_canvas.py covers per-paint default refresh, native item recreation and style cleanup after errors on Linux Tk 8.6 |
| Display/platforms | Unverified | Check display scaling, other platforms, and broader cookbook interactions, including the cookbook's use of the external Sun Valley light theme |

Theme coverage: [tkinter_themes.py](../tests/tkinter_themes.py) checks all implemented widget families across installed themes. macOS Tk 9.1 was checked with aqua, clam, alt, default and classic; Linux Tk 8.6 was checked with clam, alt, default and classic. Windows rendering and third-party themes still need runtime verification. The macOS fullscreen-exit timeout also occurs with the original backend.

Sizing policy coverage: [tkinter_sizing.py](../tests/tkinter_sizing.py) checks nested container expansion, sibling priority, explicit weight ratios and redraw updates against doc/Layout.html.

Existing suites: [tkinter_regression.py](../tests/tkinter_regression.py),
[tkinter_views.py](../tests/tkinter_views.py), [tkinter_table.py](../tests/tkinter_table.py),
and [tkinter_lifecycle.py](../tests/tkinter_lifecycle.py).
Constructor argument compatibility is checked by
[signature_regression.py](../tests/signature_regression.py); native layout and
platform checks above remain pending.
Run `env/bin/python -m unittest discover -s tests -p 'tkinter_*.py' -v`.
The recorded env/ runtime is Python 3.14.4 with the matching local Tk package and
system Tcl/Tk libraries. Canvas cookbook coverage skips cubic drawing.
Passing the suite does not complete the pending native checks above.
Legacy decorator warnings, metadata, and argument forwarding are checked in
[decorator_signatures.py](../tests/decorator_signatures.py). Native Tk validation
on Python 3.9 remains pending; constructor/decorator checks in the separate
[Python 3.9 baseline](../README.md#python-39-compatibility) do not cover native Tk behavior.

## Decisions to discuss

- Layout: agree dimension units and wrapper sizing.
- Canvas: agree cubic rendering and text bounds/anchors; smooth Tk lines do not
  establish compatibility with the common cubic API.
- Images, HTML/Markdown, geometry, and Matplotlib: approve dependencies or define
  a limited native contract; avoid custom parsers/resamplers.
- Data views, Splitter/Modal, and desktop components: agree native composition,
  editing, ownership, and feature scope.
- Shared drag/drop and Canvas contracts: see [wx-progress.md](wx-progress.md).

## Baseline and process

Use backend `Application`/`PUIView` classes for new code and examples. Keep
deprecated decorators covered by compatibility checks during migration.

PySide6 baseline for all modules: `2b06235fdbbec6e09195ce714c117b03677c6303`.
`95e6cff` supersedes Window/Modal state, Base size policies/redraw guards,
ComboBox invalid selection, and TextField edit caching. `9a3b142` supersedes
ComboBox free-text handling, `675e831` editor/quit lifecycle, and `b9e3ad5`
Tabs placement. Pin newer component SHAs only when adopting later reference behavior.
For Window state, follow the current [initial-only declaration contract](Reference.html#window)
instead of the imperative methods introduced in `95e6cff`.

Work through remaining priorities; skip decisions requiring user input and
continue independent items. Preserve native geometry/ownership. Update this
document, relevant references, and Changelog.txt after each change; validate and
commit each completed change. Remove finished rows, retain pending checks, and
avoid temporary artifact paths.
See [README](../README.md) for installation and [common reference](Reference.html)
for implemented behavior.

## Visibility checks

- **Unverified:** macOS/Windows focus handling when `.visible(False)` hides the focused control; Linux retained-control toggling is covered by regression tests.

Adaptive Layout: content-size observations, retained State and threshold transitions have Linux regression coverage; macOS/Windows theme, DPI and nested scrolling geometry checks remain.
