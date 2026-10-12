# flet alignment progress

## Baseline and process

PySide6 baseline for all modules: `2b06235fdbbec6e09195ce714c117b03677c6303`.
`95e6cff` supersedes Window/Modal state, Base size policies/redraw guards,
ComboBox invalid selection, and TextField edit caching. `6722caa` supersedes
ProgressBar fractional range conversion. `9a3b142` supersedes ComboBox free-text
handling, `675e831` editor/quit lifecycle, and `b9e3ad5` Tabs placement. Record
newer component SHAs only when adopting later behavior.

Work in order: P0 lifecycle, existing controls/layout/scroll, missing components.
Update this document, both references, and Changelog.txt with each change; check
and commit completed changes. Defer dependencies and substantial native choices.

## Current status

PySide6/Tk Tabs apply native placement; Flet supports native NORTH/SOUTH.

Focused editors commit before click callbacks on supported controls. Flet tracks
native focus without an undocumented blur method and dispatches imperative
window-state changes to its session loop. Qt/wx ignore stale queued quit calls;
Flet quit tears down PUI timers/views before closing the native window.


ComboBox now shares selection/free-text resolution: selected items display their
labels while text_model stores values; free typing clears index_model to -1 and
survives redraws, including with both models bound. Unbound selections preserve
keyed identity. This also corrects clear PySide6 edit-buffer loss.


| Priority | Area | Status |
| --- | --- | --- |
| P0 | Views/lifecycle | FView/PUI coalesce redraws on the session loop; current context preserved; destroyed nodes ignored |
| P0 | Mutation batching | One page update after reconciliation; no child update calls or blanket native exceptions |
| P1 | Window | Page.window API, initial flags, imperative maximize/fullscreen, icon/size/title |
| P1 | Controls | Current Button(content), Label container clicks/selectable Text taps, editor/check/radio binding and callback reuse |
| P1 | Layout/style | Native Container shells hold weight, dimensions, four-side padding/margins and backgrounds; text styles reset |
| P1 | Scroll | Native async scroll_to requests and auto_scroll END; client behavior checks pending |
| P2 | Tabs | Current Tabs/TabBar/TabBarView; native page identities/selection preserved across keyed moves |
| P2 | Stack | Native Stack composition with native paint ordering |
| P2 | Canvas | Current Text/Path/Rect/Oval; cubic paths, resize dimensions, rotation; no infinite widget size |
| P2 | Image/ComboBox | Native image bytes/reload and Dropdown with typed item values and editable text |
| P2 | Table | Built-in DataTable with Dropdown choices and typed dialog editing; native editing/scrolling checks passed |
| P1 | Progress | Fractional value clamp and native zero-range indeterminate state |
| Packaging | Runtime | Optional QPUIQ[flet] extra targets Flet >=1.0.4,<2 |

Tabs supports NORTH/SOUTH; EAST/WEST require a separate native design. Inherited
container fonts, canvas resources/pointer events, and missing components remain pending.

## Runtime and validation

User decision: use latest Flet. Installed flet/flet-desktop/flet-web 1.0.4 in
env/ and migrated directly to the 1.x APIs without compatibility shims.
Reference: [official migration guide](https://flet.dev/docs/updates/migrate-to-1-0/).

`env/bin/python -m unittest discover -s tests -p flet_regression.py -v`:
9 real-Flet Session/patch/control tests passed using a recording message
transport. They cover native constructors, style/binding reuse, keyed Tabs
selection, initial window state, editor commits, redraw batching, Dropdown values, native
canvas shapes, image bytes, progress clamp, END request configuration, and native
label event routing with callback replacement/removal. This is
framework/session coverage, not a Flutter visual-client test. Syntax/import
checks pass; Live web-client smoke checks passed for counter updates, editor commits,
Tabs switching, and canvas text/rectangle/cubic rendering. Snapshot:
`/tmp/pui-flet-smoke.jpg`. A separate live label check confirms ordinary and
selectable clicks, callback replacement/removal, and editor commit before clicks.
The original callback-only test missed that Text.on_tap only fires for selectable
text; ordinary labels now use the existing native Container.on_click.
All 19 supported cookbook pages cycle through a real serialized
Flet Session without update errors; this does not verify their complete visual
layout or interactions. Standalone Scroll interaction checks remain pending. Worker-thread tests require
normal process socket access: the sandbox blocks asyncio executor shutdown
wakeups; a standalone stdlib reproducer passes outside it. No Python patch or
production workaround was added.

## Table

User decision: use Flet's built-in DataTable. No additional dependency is needed.
PySide6 Table reference: `0cb3fe0a186af08ef9b91b0f22a6743218daedc8`, superseded
by `df4cbac` for adapter refresh.

Table/TableNode render declarative rows or BaseTableAdapter data. Explicit counts
and headers determine declarative dimensions; ragged/missing cells are inert
blanks, and tables with no native columns render an empty surface. Row headers occupy a separate
first column without changing adapter callback indices. Native Row and Column
containers provide scrolling. DataTable sizes columns from their contents;
autofit=False is explicitly unsupported. Headers scroll with the data.

Editable choice cells use Dropdowns with unique option keys, preserving raw value
types even when labels repeat. Choices alone do not enable editing. Editable
choice cells give gestures to the Dropdown, so cell click/double-click callbacks
apply to ordinary cells. A choice cell
with an explicit display value shows it as the Dropdown label. Other editable
cells open an AlertDialog with Save/Cancel. Strings, integers, floats, booleans,
and None (edited as text) are supported; other object types remain read-only.
Numeric input is validated before invoking bindings, TableNode.set, or
adapter.setData; normalized model values are rendered on redraw. Display text
and raw editing values remain separate.

Keyed TableNode rows/cells retain native identity and open drafts on reorder;
callbacks use the current declaration. Removing a cell/table, changing its raw
value, or making it read-only cancels its draft. Adapters expose positional indices
without stable row keys, so any table reconciliation cancels an adapter dialog.
This prevents a draft being committed into a reordered row. Single/double-tap
callbacks retain logical data coordinates. Selection and keyboard navigation
follow native Flet behavior rather than Qt's cell-selection model.

Validation: 12 new real-Flet Session tests pass, including native shape validation,
headers/ragged/empty transitions, typed duplicate-label choices, raw/display
separation, validation, cancellation, normalized callback results, keyed moves,
callback rebinding/removal, stale editor prevention, and adapter dimension changes.
Dialog validation errors use Flet 1.x TextField.error. Dialog changes are sent
through targeted Page.update(dialog) calls; table reconciliation still batches
its normal page update. The transport serializes the native MessagePack protocol,
including a regression asserting that validation text is sent to the client.
The existing 9 Flet regression tests also pass. Live web checks confirm bound
text edits, integer validation, adapter edits updating two tables, Cancel,
duplicate-label choices, keyed row moves and editing the moved cell, ordinary
cell clicks, and horizontal/vertical scrolling. Both Table cookbook pages are
enabled. Native double-click/keyboard ordering remains unverified: the browser's
accessibility double-click actions produced single clicks; Session dispatch tests
cover double_tap routing. Snapshot: `/tmp/pui-flet-table-smoke.jpg`.
Large tables still materialize all cells; no paging or virtualization contract
has been added.

## Decisions to discuss

- Table: non-content column sizing (autofit=False), additional editor types,
  stable adapter row identities, and large-data paging need API decisions.

- Canvas ImageResource crop/scale/source rectangles need a server-side decoder
  (such as Pillow); no extra imaging dependency has been installed.
- Native canvas pointer event composition and text height clipping remain pending.
- Grid row/column spans do not map directly to native GridView; agree the layout
  strategy instead of adding manual pixel-position algorithms.
- Imperative dialogs are async services in Flet 1.x; agree the common return/API
  contract before emulating synchronous dialogs.

- Decide which PySide6 desktop features should remain unsupported in this
  single-window backend.
- Shared drag/drop, Canvas anchor/bounds, and cancellation decisions are recorded
  in wx-progress.md.

## Installation

Backend extras are declared in setup.py: pyside6, wx, flet, textual, and tkinter.
The Tk extra is empty because Tk is native Python/OS support. Generated egg-info
metadata confirms all five extras and their conditional dependencies. See the
README for published-package and local env/ installation commands.
