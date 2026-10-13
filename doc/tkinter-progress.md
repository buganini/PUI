# tkinter alignment progress

Only unfinished work is listed below. **Missing** means the named behavior has
no implementation; **Partial** means an implementation exists but the listed gap
remains; **Unverified** means code exists but the stated runtime check is pending.
Completed changes belong in the changelog and reference, not the backlog.

## Missing or incomplete behavior

| Priority | Area | State | Remaining work |
| --- | --- | --- | --- |
| P1 | Canvas events | Missing | Wire `.mousedown`, `.mouseup`, `.mousemove`, `.mouseenter`, `.mouseleave`, `.dblclick`, and `.wheel`, including coordinates/buttons/modifiers |
| P1 | Canvas sizing/repaint | Partial | Use actual allocated dimensions instead of requested dimensions, repaint on native resize, and honor the painter's immediate-redraw return value |
| P1 | Window keyboard/icon | Missing | Implement `.keypress` forwarding and the common icon option |
| P1 | Window close lifecycle | Partial | Agree last-window close behavior with the hidden Tk root; connect native close to PUI teardown |
| P1 | Layout dimensions | Partial | Resolve pixel dimensions versus Tk text character/line units and wrapper sizing |
| P1 | Selectable text | Missing | Honor Label/Text `selectable`; both currently use ordinary tk.Label widgets |
| P2 | Canvas curves/geometry | Missing | Implement `drawCubicBezier` and `drawShapely`; agree a renderer/approximation and optional dependencies first |
| P2 | Canvas images | Missing | Implement ImageResource/loadImage/drawImage with agreed format, crop, scale, and opacity support |
| P2 | Canvas text/HiDPI | Partial | Implement text height clipping, resolve shared bounds/anchors, and report actual display density instead of the fixed 1.0 fallback |
| P2 | Image | Missing | Implement the standalone Image control; agree formats/scaling before adding dependencies |
| P2 | Stack/Splitter/Modal | Missing | Choose native composition and lifecycle, then implement reconciliation |
| P2 | Table/Tree | Missing | Agree native data views, editing, and selection/expansion preservation |
| P3 | HTML/Markdown | Missing | Choose native support or approve dependencies; current classes display plain text |
| P3 | Menus/toolbars/MDI/interop | Missing | Define supported desktop scope and native ownership before implementation |
| P3 | MatplotlibCanvas | Missing | Agree integration and approve the optional dependency |
| Shared | Drag/drop | Missing | Define common payload/lifecycle semantics before implementation |

Canvas callback registration is inherited from PUINode, but Canvas and
TkBaseWidget do not bind these input events. Existing shape drawing tests do
not establish pointer-event support.

## Validation still needed

| Area | State | Pending check |
| --- | --- | --- |
| Views | Unverified | Manual focus/keyboard transitions and other platforms; selection, retained edits, keyed moves/removal and model replacement are covered by tests/tkinter_views.py |
| Tabs models | Unverified | Broader keyboard/focus and platform behavior; native selection events, optional models, duplicate keys, keyed moves, labels and empty transitions are covered by tests/tkinter_tabs.py |
| Scroll | Unverified | Exercise resize, END following, content growth, user-position preservation, and local wheel behavior |
| Dialogs | Unverified | Operate native dialogs; current helper tests check argument/result conversion |
| Window | Unverified | Broaden native state/close checks, accounting for window-manager acknowledgement |
| Layout/Tabs | Unverified | Compare geometry, resizing, and ttk tab placement with PySide6 |
| Display/platforms | Unverified | Check display scaling, other platforms, and broader cookbook interactions |

Existing suites: [tkinter_regression.py](../tests/tkinter_regression.py) and
[tkinter_views.py](../tests/tkinter_views.py).
Constructor argument compatibility is checked by
[signature_regression.py](../tests/signature_regression.py); native layout and
platform checks above remain pending.
Run `env/bin/python -m unittest discover -s tests -p 'tkinter_*.py' -v`.
The recorded env/ runtime is Python 3.14.4 with the matching local Tk package and
system Tcl/Tk libraries. Canvas cookbook coverage skips cubic drawing.
Passing the suite does not complete the pending native checks above.
Legacy decorator warnings, metadata, and argument forwarding are checked in
[decorator_signatures.py](../tests/decorator_signatures.py); Python 3.9 runtime
validation remains pending because that interpreter is not installed locally.

## Decisions to discuss

- Layout and window lifecycle: agree dimension units/wrapper sizing and
  last-window behavior with the hidden root.
- Canvas: agree cubic rendering and text bounds/anchors; smooth Tk lines do not
  establish compatibility with the common cubic API.
- Images, HTML/Markdown, geometry, and Matplotlib: approve dependencies or define
  a limited native contract; avoid custom parsers/resamplers.
- Data views, Stack/Splitter/Modal, and desktop components: agree native composition,
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

Work through remaining priorities; skip decisions requiring user input and
continue independent items. Preserve native geometry/ownership. Update this
document, relevant references, and Changelog.txt after each change; validate and
commit each completed change. Remove finished rows, retain pending checks, and
avoid temporary artifact paths.
See [README](../README.md) for installation and [REFERENCE.md](../REFERENCE.md)
for implemented behavior.
