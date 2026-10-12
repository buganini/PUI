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
| P2 | Table | Compatibility reviewed; DataTable2 proposed, Dropdown/dialog editing agreed; PUI wrapper pending |
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
All 17 supported cookbook pages cycle through a real
Flet Session without update errors; this does not verify their complete visual
layout or interactions. Scroll interaction checks remain pending. Worker-thread tests require
normal process socket access: the sandbox blocks asyncio executor shutdown
wakeups; a standalone stdlib reproducer passes outside it. No Python patch or
production workaround was added.

## Table compatibility and plan

Checked against Flet 1.0.4 and the published flet-datatable2 1.0.4 wheel/source.
The extension requires exactly `flet==1.0.4`, matching env/. It was downloaded for
inspection, not installed or added to setup.py. PySide6 Table reference:
`0cb3fe0a186af08ef9b91b0f22a6743218daedc8`, superseded by `df4cbac` for adapter
refresh. PUI's Flet Table/TableNode remain unimplemented.

DataTable2 is the preferred candidate for its native scrolling, fixed headers,
fixed left columns, and explicit/relative column widths. It retains DataTable's
cell content/event model; it does not supply PUI binding, adapters, or automatic
editing. See [DataTable2](https://flet.dev/docs/controls/datatable2/) and
[DataColumn2](https://flet.dev/docs/controls/datatable2/datacolumn2/).

User-agreed editing plan:

1. Map TableNode rows/cells and BaseTableAdapter values into native table rows.
   Preserve display text separately from raw values and rebind current callbacks.
2. Put a native Dropdown in editable cells with choices. Use unique option keys
   to preserve raw values/types even when labels repeat. Choices alone do not
   make a read-only cell editable.
3. Open a native dialog for other editable cells. Initialize it from editData/raw
   data; Save validates and commits through setData, the binding, or TableNode.set;
   Cancel discards the draft. Handle results asynchronously within the event
   handler, without a nested event loop or changes to generic dialog APIs.
4. Preserve read-only display and click/double-click callbacks. Keep editor
   identity tied to the current row/cell; removal cancels editing rather than
   committing to a stale index. Test edits, cancellation, rebinding, and redraws
   through the native UI before enabling either Table cookbook page for Flet.

Remaining compatibility boundaries:

| Contract | Assessment |
| --- | --- |
| Headers | Column headers map directly. Row headers need an extra first column; DataTable2 can freeze it, with logical data indices kept separate. |
| Empty/ragged data | Native shape validation requires at least one column and rectangular rows. Pad missing cells with inert blanks; render a zero-column PUI table as an empty surface. DataTable2's empty control covers zero rows, not zero columns. |
| Column sizing | DataTable2 provides fixed widths and relative S/M/L sizes, which do not reproduce Qt resizeColumnsToContents/autofit. Agree the supported sizing behavior before implementation; avoid custom text measurement. |
| Editing types | Dropdown keys can preserve arbitrary choice values. Dialog validation must preserve supported raw types and normalized adapter/binding results; a text field alone is not a typed Qt delegate. |
| Selection/gestures | Native row selection differs from Qt cell selection. Single/double tap event APIs exist; exact keyboard behavior and click/double-click ordering need native validation. |
| Large data | Both Flet APIs receive materialized row/cell controls. DataTable2 is not a drop-in replacement for Qt's model-driven view; large-data behavior needs measurement or a separate paging contract. |

Evidence: six isolated native DataTable validator/session probes passed (shape
constraints, blank/headerless configuration, row identity/event rebinding, and
embedded editors). Live web checks confirmed single-cell taps, text submit,
headerless display, and duplicate-label Dropdown selection returning an integer.
They do not establish DataTable2 client compatibility or full PUI Table parity;
DataTable2 has source/metadata review only. Its client availability/build path,
fixed headers, scrolling, and layout still need runtime checks after dependency
approval. The existing PySide6 table suite now has 13 passing tests. The audit
found and fixed an undefined adapter refresh call with a native model reset;
selection/editor state can reset with it.

## Decisions to discuss

- Approve the flet-datatable2 dependency and its matching Flet release constraint
  before installation/adoption. Keep the Dropdown/dialog editing plan above.
- Agree Table autofit behavior under DataTable2's native fixed/relative sizing.

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
