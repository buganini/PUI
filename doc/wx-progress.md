# wx alignment with PySide6

## Goal and scope

Make backend-neutral PUI applications behave consistently when switching from
`PUI.PySide6` to `PUI.wx`: declarations, state binding, event payloads, updates,
layout, and component APIs. Use the current PySide6 implementation and cookbook
as the behavior reference, while preserving native wx ownership and event-loop
rules. Qt-specific `.qt(...)` options and Qt widget types are outside the parity
contract; native appearance need not be pixel-identical.

This is an implementation plan based on source inspection on 2026-10-12. Implementation has started; the change log below records completed work and
validation.
All unchecked items remain pending. If reference behavior is defective or
ambiguous, document the intended shared contract before implementing it.

## Current coverage

| Area | wx status relative to PySide6 | Priority |
| --- | --- | --- |
| Application and views | Application/PUIApp exist; wx queues every redraw and has no backend-specific PUI decorator | P0 |
| Lifecycle and parenting | Native reuse exists, but destruction, queued work, child replacement, and parent ownership need verification | P0 |
| Layout | HBox/VBox/Spacer/Grid exist; expansion bookkeeping, dynamic proportions, asymmetric padding, and grid changes need alignment; Stack missing | P0/P2 |
| Common controls | Button/Checkbox/RadioButton/ComboBox/TextField/Label/Text/ProgressBar/Divider exist; binding, event, and mutable-property parity needs validation | P1 |
| Styling | wx applies font size and foreground with truthiness checks; generic font family/background handling and style reset are incomplete | P1 |
| Scroll | Container exists; scrollX/scrollY are no-ops | P1 |
| Dialogs/windows | Helpers exist; argument differences and mutable window state need alignment | P1 |
| Canvas | Drawing and pointer events exist, including pixel_density; cubic Bezier, image resources/drawing, enter/leave events missing | P2 |
| Text/image | selectable is stored but unused in wx Label/Text; Html/MarkDown explicitly unsupported; Image missing | P2 |
| Containers | Tabs/Tab, Splitter, Modal missing | P2 |
| Data views | Table/TableNode and Tree/TreeNode, including adapter paths, missing | P3 |
| Desktop integration | Menus, toolbar, MDI, native widget embedding, and MatplotlibCanvas missing from wx | P3 |

Relevant sources: `PUI/wx/`, `PUI/PySide6/`, `PUI/view.py`, `PUI/node.py`,
`PUI/dom.py`, `PUI/interfaces.py`, and `cookbook/__main__.py`. Compare actual
exports as well as modules: PySide6 menus are imported through its window module.

## Phase 0 — Freeze contracts and establish a runnable baseline

- [ ] Inventory public constructors, fluent methods, events, return values, and
  supported flags across both backends. Record unresolved differences here.
- [ ] Capture baseline behavior with `python -m cookbook PySide6` and
  `python -m cookbook wx`, using the same data, sizes, and interactions.
- [ ] Extract reusable backend-selectable regression scenarios from existing
  tests. Several tests, including `tests/redraw_semaphore.py`, currently import
  PySide6 directly; they cannot be assumed to exercise wx unchanged.
- [ ] Establish a wx GUI test environment with wxPython and a display (virtual
  display where available). Distinguish automated assertions from manual checks.

**Exit:** a public API checklist and reproducible baseline identify supported,
partial, missing, and intentionally backend-specific behavior.

## Phase 1 — Redraw, reconciliation, and native ownership (P0)

- [x] Add a wx-specific `PUI` decorator producing `WxPUIView`, following the
  public calling convention of PySide6's decorator.
- [x] Align dirty/updating scheduling with `PUIView.sync()`: coalesce redraw
  bursts through wx's GUI queue, avoid recursive update loops, and ignore retired
  or destroyed views. Review wx Application's initial update path as well.
- [ ] Marshal quit/native mutations to the GUI thread where needed; apply the
  application icon and verify startup and shutdown behavior.
- [x] Audit `destroy(direct)`, retired references, and event rebinding so reused
  native controls survive reconciliation and removed controls are destroyed once.
- [x] Make parent lookup safe through virtual views and new containers. Resolve
  Window's panel versus frame ownership and mount/detach replacement children.

**Exit:** redraw bursts yield a bounded number of builds; nested views, batching,
keyed insertion/removal/reordering, and hot reload preserve surviving controls.
Queued callbacks after removal do not access destroyed windows. Use scenarios
from `tests/virtual_nodes.py`, `tests/nested_view.py`, `tests/subview_id.py`,
`tests/batched_state_mutation.py`, and `tests/redraw_semaphore.py`.

## Phase 2 — Layout and shared styling (P0/P1)

- [x] Recompute expansion priorities and child counts per update rather than
  allowing accumulated bookkeeping. Explicitly reset proportions when weight
  changes to zero or is removed.
- [x] Define generic width/height behavior against PySide6 size hints; test
  shrinking as well as growth and removal of explicit dimensions.
- [x] Preserve all four padding values instead of reducing them to `max(...)`;
  use suitable wrapper panels/sizers when needed. Match default outer padding.
- [x] Reconcile grid position/span changes and resizing after child replacement.
- [x] Apply font size/family, foreground/background, including black (`0`) and
  removal of previously applied styles. Avoid accumulating stale native styles.

**Exit:** HBox/VBox/Grid cookbook scenarios resize correctly, and repeated
weight, dimension, padding, and style changes give stable geometry. Validate
asymmetric padding and virtual children explicitly.

## Phase 3 — Existing widgets, scrolling, and dialogs (P1)

- [x] Align TextField input versus commit behavior, Enter/focus handling,
  edit_model, and programmatic model changes. Prevent programmatic text updates
  from masquerading as user input; preserve focus/caret during unrelated redraws.
- [x] Audit Checkbox and RadioButton scalar/collection binding and ensure every
  callback resolves the current node and current value after reuse.
- [x] Harden ComboBox against empty items, invalid indices, changed item labels
  or values, reorder/removal, and editable mode changes. Verify exactly one
  callback with the agreed payload per user action.
- [ ] Verify mutable labels, progress ranges/values (including fractional public
  values versus wx's integer gauge), divider behavior, and click callbacks.
- [ ] Implement scrollX/scrollY with PySide6's positive/negative offset and END
  semantics, preserving user position and end alignment when content grows or
  shrinks. Apply requests after layout establishes the scroll range; support
  dynamic axis options and replacement content.
- [ ] Align dialog keyword APIs (`dir` in PySide6 versus `directory` in wx),
  allowing compatibility aliases; make SaveFile's default optional. Match file
  filters, default paths, result types, and cancellation per helper. Resolve
  OpenDirectory's current empty-string versus None difference explicitly.
- [x] Make maximize/fullscreen transitions honor both True and False; handle
  unset icon/size safely and verify close/quit accelerator behavior.

**Exit:** shared control, binding, scroll, and dialog cookbook examples work
under wx. Automated checks cover model-to-widget and widget-to-model updates,
event counts, invalid selections, scroll range changes, and window transitions;
native dialogs and focus behavior receive manual checks too.

## Phase 4 — Common missing visual components (P2)

- [ ] Add Stack with overlay ordering matching PySide6's StackAll behavior.
- [ ] Add Tabs/Tab, including tab placement, dynamic labels, ordering, and removal.
- [ ] Add Splitter with orientation, resizing, and dynamic child reconciliation.
- [ ] Add Modal with status/offValue binding, close synchronization, and child
  ownership; ensure showing a modal does not break reactive updates.
- [ ] Implement Image and selectable text. Evaluate native rich text/HTML support
  for Html/MarkDown; explicitly document any remaining rendering limitations.
- [ ] Complete Canvas methods: drawCubicBezier, ImageResource load/crop/scale,
  loadImage/drawImage, and pointer enter/leave. Compare coordinate conventions,
  text anchors/rotation, wheel payloads, colors, and painter state restoration.
  Fix the wx drawRect x-origin calculation (`min(x1, x1)`). Preserve logical
  coordinates and update pixel_density before painting.

**Exit:** newly supported cookbook pages can be enabled for wx with verified
behavior. Canvas checks cover reversed rectangle coordinates, images, curves,
and display scaling; visual comparisons allow native rendering differences.

## Phase 5 — Data views and desktop integration (P3)

- [ ] Implement Table/TableNode with both declarative and BaseTableAdapter paths:
  headers, ragged rows, editable cells, choice editors, and click/double-click.
- [ ] Implement Tree/TreeNode with BaseTreeAdapter support: hierarchy updates,
  expansion/collapse, editing, drag/drop, and current-node event resolution.
- [ ] Add generic drag/drop hooks to appropriate widgets and layouts; document
  native event-object differences for backend-specific handlers.
- [ ] Add MenuBar/Menu/MenuAction and ToolBar/ToolBarAction with dynamic actions
  and callback rebinding; integrate their ownership into Window.
- [ ] Add MdiArea/MdiSubWindow and wx-native embedding equivalents to QtInPui and
  PuiInQt. Choose explicit wx names and preserve externally owned widgets.
- [ ] Add MatplotlibCanvas using the wx integration, keeping plotting dependencies
  optional and unrelated backend imports usable without them.

**Exit:** table/tree cookbook examples and equivalent assertions from
`tests/table_ragged.py` and `tests/tree_sync.py` pass on wx. Desktop integration
examples survive action/child replacement and window closure.

## Delivery and completion

### Change log

- 2026-10-12: P1 controls/dialog API: TextField uses silent native updates,
  resolves current nodes, preserves edit buffers, and commits once on Enter or
  focus loss. Checkbox callbacks use current values. ComboBox refreshes choices
  and handles empty/invalid selection; progress uses integer hundredths as in
  PySide6. Dialogs accept `dir` and the legacy `directory` alias, Qt/wx filter
  forms, and optional SaveFile defaults. Validation: 9 GUI/helper checks passed.
  Native dialog interaction and mutable ComboBox editability still need manual
  checks; these are not marked fully complete.

### Decisions to discuss later

- OpenDirectory cancellation differs between PySide6 (empty string) and wx
  (None). Kept existing behavior pending a shared contract decision.
- Rich Markdown rendering would require either an added dependency or an agreed
  limited renderer. Do not introduce a hand-written Markdown parser.
- Cross-platform native drag/drop needs a public backend-neutral payload contract;
  Qt event objects cannot be passed to wx handlers. Defer until that is agreed.

### Remaining validation

PySide6 is not installed in this environment. Runtime comparisons against Qt,
manual dialogs/focus/display scaling, and other desktop platforms remain pending.

- 2026-10-12: P0/P1 layout/style: removed accumulated expansion counters;
  compute proportions from current mounted children and reset zero weights.
  Added four-sided padding wrappers, shrinking/resetting minimum dimensions,
  grid replacement coverage, native style restoration, font family/weight, and
  zero-valued foreground/background colors. Validation: 7 native GUI checks
  passed, including keyed reorder/removal through padding wrappers. Width and
  height remain wx minimum-size hints; pixel-identical Qt geometry is not promised.

- 2026-10-12: P0 scheduling/ownership change: added wx `PUI`, coalesced queued
  redraws using the shared sync lifecycle, guarded retired/destroyed views,
  queued application quit, reused an existing wx.App, corrected native parenting
  through virtual views, and mounted window content in its panel. Destruction
  now respects direct ownership; detached layout subtrees clear owned windows.
  Window size/icon None and false maximize/fullscreen transitions are handled.
  Validation: wxPython 4.2.4 GTK display startup passed outside the sandbox;
  5 native GUI regression checks passed with `python3 -m unittest discover
  -s tests -p wx_regression.py -v` (Linux GTK). PySide6 is not installed;
  comparative runtime checks remain pending.

Implement in dependency order: contracts → lifecycle → layout → existing
controls/scroll → visual containers → data views/desktop integration. Keep each
change scoped to one behavior or component family, with its regression evidence.

- [ ] Update this checklist after each delivery with changed files, validation
  commands/results, remaining limitations, and any agreed contract decisions.
- [ ] Enable wx cookbook capability flags only after validating each feature;
  review the currently excluded State Binding and TimelineView examples too.
- [ ] Document remaining backend-specific APIs and unsupported features in the
  reference and README. Avoid silently successful no-op parity methods.
- [ ] Run the full shared regression set and cookbook on PySide6 and wx; verify
  resize, focus, dialogs, scrolling, and display scaling on supported desktop
  platforms, recording the platforms actually checked.

Alignment is complete when the agreed backend-neutral API inventory is covered,
shared behavior checks pass, and every remaining difference is explicitly
documented. Completing only the existing wx controls is an intermediate milestone.
