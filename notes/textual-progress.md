# Textual alignment plan and progress

Latest runtime audit: [2026-10-28 macOS validation](validation-2026-10-28.md).

Autocomplete follows the [shared acceptance criteria](https://buganini.github.io/PUI/doc/Reference.html#autocomplete-acceptance).

**Pending** items have not been aligned; **Partial** items have the listed gaps.
Existing modules may be partial; their presence is not a completed alignment item.
Keep only functional gaps, known bugs and design decisions in the backlog.

Implemented integrations are **complete**. This backlog tracks missing functionality,
known bugs and design decisions. Additional test coverage does not keep a feature
open. Detailed test environments, results and follow-up QA are in
[validation notes](validation-2026-10-30.md#textual). Platform names below identify
known differences or specific bugs, not a mandatory three-OS completion matrix.

## Baseline and process

Use backend `Application`/`PUIView` classes for new code and examples. Keep
deprecated decorators covered by compatibility checks during migration.

Original source audit: `e3896702b007b41aef479abeea1bd35fb7991fc1` (2026-10-12).
Use the current shared contracts and backend reference for subsequent changes;
the original audit is historical context, not a freeze on later layout/API fixes.
This includes the initial-only window-state contract, ComboBox free-text fixes,
editor lifecycle corrections, fractional progress ranges, and tab placement.
Record the relevant reference behavior and focused test when changing a component.

Align declarations, state binding, callbacks, reconciliation, and supported
layout behavior while preserving native terminal interaction. Pixel rendering,
OS window management, and Qt-specific options require explicit capability
boundaries rather than simulated parity.

Work through P0, then P1, then native P2 additions. After each completed change,
update this document, [common reference](https://buganini.github.io/PUI/doc/Reference.html), relevant cookbook flags,
and Changelog.txt; run the relevant checks and commit the change. Keep this
document focused on missing/partial behavior, unchecked work, and decisions.
Do not include completed implementation summaries or temporary artifact paths. Skip items
that need a dependency or substantial technical decision and continue independent
work. Use public Textual APIs; avoid monkey patches, custom event loops, and
rebuilding entire widget trees to conceal ownership bugs. Fix a clear PySide6
reference bug when found and record the new reference commit.

## Runtime and audit context

The recorded runtime in `env/` is Textual 8.2.8. The existing `QPUIQ[textual]`
extra declares `textual` without a version bound. Native headless Views checks
are in [textual_views.py](../tests/textual_views.py); they do not establish general
backend alignment. The repository also has a manual scroll example in
[tests/layout/textual_scroll.py](../tests/layout/textual_scroll.py).
Legacy decorator warnings, metadata, and argument forwarding are checked in
[decorator_signatures.py](../tests/decorator_signatures.py). Textual validation
on Python 3.9 remains pending; the separate
[shared/Qt Python 3.9 check](../PUI/doc/pyside6-reference.md#python-39-compatibility) does not cover Textual.

Existing adapters include Grid, Splitter, ComboBox/ComboBoxItem, TextEdit and
MaskedField as well as the basic controls. Their remaining gaps are listed below.
Stack uses VBox as a reversed vertical fallback; overlapping children are not supported.
Canvas is an unsupported placeholder and Html explicitly reports unsupported.
Do not infer support for pixel graphics or native-widget embedding from exported names.

## Prioritized work

Source findings identify what to reproduce before changing behavior. The table
lists only outstanding behavior; the Views suite does not validate unrelated modules.

| ID | Priority | State | Finding and planned change | Acceptance check |
| --- | --- | --- | --- | --- |
| T1 | P0 | Partial | Application and TPUIView queue redraws; TPUIView also guards retired/destroyed nodes and reapplies layout after reconciliation. Audit worker-thread dispatch, Application teardown races and legacy decorated views for the same coalescing/ownership guarantees. | State changes from clicks, subviews, and a worker update once per burst on the app loop; retired/removed nodes do nothing; quit stops timers. |
| T2 | P0 | Partial | General layout removal outside Views/Tabs still calls Widget.remove() during keyed moves. Audit mount/remove ordering, virtual parents, root replacement, and empty Scroll children. | Insert, reorder, replace, and remove general keyed controls without duplicate mounts, lost focus/edit buffers, orphan widgets, or events reaching removed nodes. |
| T3 | P0 | Partial | Label.postUpdate() repeatedly mounts its existing child. Audit clickable/plain transitions and asynchronous mount/removal boundaries. | Repeated label updates and clickable/plain transitions preserve correct ownership without duplicate mounts. |
| T4 | P0 | Pending | Application has no quit implementation, does not handle native child removal, and assumes every bubbled widget event has puinode. Complete native App.exit()/PUI teardown and guard event ownership/current-node resolution. | Exit through the PUI API and native app shutdown releases timers/views; unrelated native widgets and delayed events do not crash event dispatch. |
| T6 | P1 | Partial | TextField still commits only on submit. Complete blur/before-click commits and normalized-value handling; broaden rebinding and rapid-update checks. | Model rebinding, normalized values, Enter, blur, and click-after-edit preserve the current edit and produce one change callback. |
| T7 | P1 | Pending | Checkbox/RadioButton do not refresh labels or invoke click callbacks; programmatic values may emit native change messages. Label/Text ignore selectable; clickable Label changes native widget type. Verify literal text, native focus/keyboard activation, current handlers, and message suppression. | Pilot mouse/keyboard actions invoke the current callback once; removed handlers stop firing; programmatic updates stay silent; markup-like labels remain literal. Selection behavior waits for D2 if native support cannot match it. |
| T8 | P1 | Pending | Scroll.scrollX/Y only store offsets; update neither applies nor preserves them. Implement start/end requests, END, user-position preservation, axis policies, and content-growth/resize handling after native layout. | Native scrolling reaches requested start/end positions, retains manual position across unrelated redraws, follows END on growth, and tolerates empty/replaced content. Scroll offset units still need a separate contract. |
| T10 | P1 | Pending | ProgressBar scales values but has no explicit range/zero policy. Application.title already sets the native app/terminal title; Window.title is intentionally ignored. Audit ProgressBar range/zero handling, unsupported Window parameters and keyboard forwarding. | Fractional/range updates and the agreed zero-range indicator work; Application title remains startup configuration; desktop-only state follows the capability decision in D3. |
| T11 | P1 | Pending | Canonical exports and unsupported capability reporting are inconsistent. Add truthful canonical placeholders/aliases and audit the reference matrix and cookbook X flags against native checks. | Common imports and supported examples run; missing features never appear implemented solely because a name exists or a call silently returns None. |
| T14 | P3 | Pending | Evaluate remaining general screens and desktop/graphics features only after existing components are stable. Tree/TreeNode and adapter support now use the native Tree; Pilot verifies callbacks, keyboard/mouse input, retained selection/expansion and cookbook additions. | Define the supported subset and interaction contract before advertising parity or writing custom editors/renderers. |
| T15 | P2 | Partial | Table lacks cell widgets, drag/drop or header sorting, native column resizing and Qt-style multi-selection. Cell callbacks follow native activation rather than every raw click. | Agree any expanded interaction contract before adding custom gestures or renderers. |

The shared DOM currently expresses some moves as remove/add operations. T2 must
first determine whether a backend-local native operation queue can preserve that
contract. If a shared reconciliation API change is necessary, record a concrete
proposal and defer that change for discussion.

## Decisions to discuss

- **D2 — Text interaction:** define selectable text/copy behavior and whether
  clickable labels enter the keyboard focus order; use native facilities and
  retain literal text rather than Rich markup unless explicitly requested.
- **D3 — Window and desktop scope:** retain one terminal screen with a startup Application
  title; reactive title binding would be a separate extension. Decide how size, maximize/fullscreen, menus/toolbars, MDI, and
  native interop report unsupported behavior. The shared maximize/fullscreen
  contract is initial-only, with equivalent constructor arguments and declarative
  setters; do not introduce reactive props or imperative state methods.
- **D4 — Data views:** agree tree identity/expansion preservation; table interaction
  extensions are tracked in T15. ComboBox acceptance gaps are tracked in T13.
- **D6 — Graphics and dependencies:** Canvas, general Image, HTML rendering,
  Matplotlib, and terminal graphics protocols need a defined terminal contract
  and possibly extra dependencies. Leave them explicitly unsupported pending
  agreement; do not create parsers or rasterizers to avoid that discussion.
- **D7 — Shared changes:** consult before modifying the shared DOM move contract,
  the established inbound drag/drop payload/lifecycle contract, or other cross-backend APIs. Continue unrelated work while
  these decisions remain open.

## Native API references

- [App API](https://textual.textualize.io/api/app/): native exit and thread-safe
  dispatch options; calling methods directly from worker threads is unsafe.
- [Widget API](https://textual.textualize.io/api/widget/): mount/remove awaitables,
  native child movement, focus, and scrolling. Account for asynchronous lifecycle
  completion rather than assuming a mount/remove call has finished immediately.
- [Events and messages](https://textual.textualize.io/guide/events/): use the
  public prevent context for programmatic change suppression.
- [Widget gallery](https://textual.textualize.io/widget_gallery/): native
  TabbedContent and Tree are candidates to assess, not
  evidence that their full PySide6 contracts already match.
