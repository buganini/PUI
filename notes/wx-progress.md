# wx alignment progress

Latest runtime audit: [2026-10-28 macOS validation](validation-2026-10-28.md).

Autocomplete follows the [shared acceptance criteria](https://buganini.github.io/PUI/doc/Reference.html#autocomplete-acceptance).

**Missing** means no implementation; **Partial** means a known functional gap.
Completed changes belong in the reference and changelog.

Implemented integrations are **complete**. This backlog tracks missing functionality,
known bugs and design decisions. Additional test coverage does not keep a feature
open. Detailed test environments, results and follow-up QA are in
[validation notes](validation-2026-10-30.md#wx). Platform names below identify
known differences or specific bugs, not a mandatory three-OS completion matrix.

## Missing or incomplete behavior

| Priority | Area | State | Remaining work |
| --- | --- | --- | --- |
| P1 | Image sizing | Partial | Scale/fill weighted images when their allocated size changes, beyond explicit dimensions |
| P2 | Table | Partial | Additional editor types and large-data optimization beyond the current per-cell attributes/content autosizing need scope decisions |
| P3 | Toolbar | Missing | Agree one native toolbar versus PySide6's multiple-toolbar model |
| P3 | MDI/interop | Missing | Agree platform scope, native hosts, and borrowed-widget ownership |
| P3 | Markdown | Missing | Markdown currently falls back to plain text |
| Shared | Drag/drop | Partial | Native Window targets support files/text/URLs; sizer-only targets and outgoing drags remain |
| Shared | Dialog cancellation | Partial | Resolve OpenDirectory's wx None versus PySide6 empty-string result |

## Decisions to discuss

- Toolbar and MDI: resolve the native choices
  listed in their backlog rows before adopting custom composition.
- Interop: agree borrowed-widget ownership and restoring original parents.
- Dependencies: approve Matplotlib, Shapely, and rich Markdown dependencies before
  installation or adding extras.
- Shared contracts: OpenDirectory cancellation.

## Baseline and process

Use backend `Application`/`PUIView` classes for new code and examples. Keep
deprecated decorators covered by compatibility checks during migration.

User decisions: use wx.grid.Grid for Table, wx.dataview.DataViewCtrl for Tree,
and nested wx.SplitterWindow controls for Splitter, nesting in the right/bottom
pane. These are included in wxPython; no new dependency is required.

Use the current [common reference](https://buganini.github.io/PUI/doc/Reference.html)
and [layout policy](https://buganini.github.io/PUI/doc/Layout.html) as the shared
contract. Historical porting baselines remain in Git history; they must not
reintroduce superseded priorities, sizing or lifecycle behavior.
For Window state, follow the current [initial-only declaration contract](https://buganini.github.io/PUI/doc/Reference.html#window)
instead of the imperative methods introduced in `95e6cff`.
Canvas style reuse follows PySide6 `8d3fa8d`; native wx DC geometry and local
GraphicsContext rendering remain in place.

Align backend-neutral declarations, binding, events, reconciliation, and layout.
Preserve native wx ownership and appearance; Qt-specific options are excluded.
Work through priorities; skip decisions requiring user input and continue
independent items. Update this document, relevant references, and Changelog.txt
after each change; validate and commit each completed change. Remove finished
rows, retain known functional gaps, and avoid temporary artifact paths.
See [README](../README.md) for installation and [common reference](https://buganini.github.io/PUI/doc/Reference.html)
for implemented behavior.

## Canvas / Matplotlib functional gaps

MatplotlibCanvas embeds FigureCanvasWxAgg, retaining native rendering, text,
path clipping and input events. Figure/canvas survive reconciliation. A PUI
navigation toolbar is still pending.

The ordinary PUI Canvas retains native rectangle/Region clipping; arbitrary path
clipping is not exposed by wx.GraphicsContext and is not approximated.
