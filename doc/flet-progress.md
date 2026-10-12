# flet alignment progress

## Baseline and process

PySide6 baseline for all modules: `2b06235fdbbec6e09195ce714c117b03677c6303`.
`95e6cff` supersedes Window/Modal state, Base size policies/redraw guards,
ComboBox invalid selection, and TextField edit caching. `6722caa` supersedes
ProgressBar fractional range conversion. `9a3b142` supersedes ComboBox free-text
handling, `675e831` editor/quit lifecycle, and `b9e3ad5` Tabs placement. Record
newer component SHAs only when adopting later behavior.
PySide6 Table reference: `0cb3fe0a186af08ef9b91b0f22a6743218daedc8`, superseded
by `df4cbac` for adapter refresh.

Work in order: P0 lifecycle, existing controls/layout/scroll, missing components.
Update this document, both references, and Changelog.txt with each change; check
and commit completed changes. Defer dependencies and substantial native choices.
Keep this document to alignment status, validation, and unresolved decisions.
API behavior belongs in [REFERENCE.md](../REFERENCE.md); implementation details
belong in source and tests. Do not record temporary local artifact paths.

## Current status

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
| P2 | Canvas | Current Text/Path/Rect/Oval; cubic paths, resize dimensions, rotation; weighted canvases fill native space and wait for a positive paint size |
| P2 | Image/ComboBox | Native image bytes/reload and Dropdown with typed item values and editable text |
| P2 | Table | Built-in DataTable with Dropdown choices and typed dialog editing; native editing/scrolling checks passed |
| P1 | Progress | Fractional value clamp and native zero-range indeterminate state |
| Packaging | Runtime | Optional QPUIQ[flet] extra targets Flet >=1.0.4,<2 |

Tabs supports NORTH/SOUTH; EAST/WEST require a separate native design. Inherited
container fonts, canvas resources/pointer events, and missing components remain pending.

## Runtime and validation

User decisions: target current Flet and use its built-in DataTable. Tested with
flet/flet-desktop/flet-web 1.0.4 in env/. See [README](../README.md) for installation,
the [Table reference](../REFERENCE.md#table) for supported editing behavior, and
the [official migration guide](https://flet.dev/docs/updates/migrate-to-1-0/) for Flet 1.x.

Run `env/bin/python -m unittest discover -s tests -p 'flet_*.py' -v`.
Last validation: 23 tests passed—11 in [flet_regression.py](../tests/flet_regression.py)
and 12 in [flet_table.py](../tests/flet_table.py). These use a real Flet Session
and serialize native patches; they do not verify Flutter rendering. Worker-thread
tests need normal process socket access for asyncio executor cleanup.

Live web-client checks passed for counter updates, editor commits, label clicks,
Tabs, fixed-size canvas drawing, and ShapeCmd's weighted canvas initial fit and
resizing. Table checks passed for choice/dialog editing, validation, cancellation,
keyed moves, callbacks, and scrolling. All 19 supported cookbook pages passed
serialized Session checks; their complete visual layout and interactions have
not been verified.

Remaining native checks: standalone Scroll interaction and Table double-click/
keyboard event ordering. Session tests cover double-tap callback routing.

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
