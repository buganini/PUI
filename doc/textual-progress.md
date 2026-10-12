# Textual alignment plan and progress

## Baseline and process

Source audit: `e3896702b007b41aef479abeea1bd35fb7991fc1` (2026-10-12).
Use that commit's PySide6 modules and shared binding helpers as the reference.
This includes the initial-only window-state contract, ComboBox free-text fixes,
editor lifecycle corrections, fractional progress ranges, and tab placement.
Keep one baseline for all modules; record a superseding component SHA only when
intentionally adopting later reference behavior.

Align declarations, state binding, callbacks, reconciliation, and supported
layout behavior while preserving native terminal interaction. Pixel rendering,
OS window management, and Qt-specific options require explicit capability
boundaries rather than simulated parity.

Work through P0, then P1, then native P2 additions. After each completed change,
update this document, REFERENCE.md, doc/Reference.html, relevant cookbook flags,
and Changelog.txt; run the relevant checks and commit the change. Keep this
document focused on current findings, unchecked work, and decisions. Skip items
that need a dependency or substantial technical decision and continue independent
work. Use public Textual APIs; avoid monkey patches, custom event loops, and
rebuilding entire widget trees to conceal ownership bugs. Fix a clear PySide6
reference bug when found and record the new reference commit.

## Current status

Planning and source inspection only; no Textual alignment changes or native
regression results are claimed. Textual is not installed in `env/`. The existing
`QPUIQ[textual]` extra declares `textual` without a version bound. The repository
has a manual scroll example in tests/layout/textual_scroll.py and layout
experiments in refs/textual_layout.py, but no dedicated Textual regression suite.

Existing modules cover Application/Window, linear layouts, Spacer, Label/Text,
Markdown, Button, Checkbox, RadioButton, TextField, ProgressBar, Scroll, and Tabs.
Presence does not establish behavioral parity. Canvas and misspelled Combobox
exports are placeholders, Divider returns None, and several canonical component
names are absent. Html explicitly reports unsupported.

## Prioritized work

All items below are pending. Source findings identify what to reproduce before
changing behavior; runtime compatibility and message ordering remain unverified.

| ID | Priority | Finding and planned change | Acceptance check |
| --- | --- | --- | --- |
| T0 | P0 | Establish a Textual runtime in env/ using the existing extra, record its exact version, and check current constructors/messages. Add a unittest async harness using App.run_test(). | Import PUI.textual; mount a minimal application; exit cleanly without pending tasks or swallowed PUI errors. |
| T1 | P0 | Application queues redraws, but TPUIView is empty and the exported PUI decorator uses synchronous shared views. Give Application, decorated views, and class subviews a consistent coalesced native queue, including worker/Timeline requests and removed-view guards. | State changes from clicks, subviews, and a worker update once per burst on the app loop; retired/removed nodes do nothing; quit stops timers. |
| T2 | P0 | TBase.destroy() ignores direct ownership; layout removal calls Widget.remove() even when the shared DOM is moving a keyed child. Audit mount/remove ordering, virtual parents, root replacement, and empty Scroll children. Use native movement for retained widgets and native removal for destruction. | Insert, reorder, replace, and remove keyed controls without duplicate mounts, lost focus/edit buffers, orphan widgets, or events reaching removed nodes. |
| T3 | P0 | Tabs.removeChild() calls removeTab() on a Textual container. Label.postUpdate() repeatedly mounts its existing child. Correct these paths and validate asynchronous mount/removal boundaries. | Repeated label updates and clickable/plain transitions work; removing the first, selected, and last tab raises no errors. |
| T4 | P0 | Application has no quit implementation, does not handle native child removal, and assumes every bubbled widget event has puinode. Complete native App.exit()/PUI teardown and guard event ownership/current-node resolution. | Exit through the PUI API and native app shutdown releases timers/views; unrelated native widgets and delayed events do not crash event dispatch. |
| T5 | P1 | TBase only writes auto/1fr sizes; explicit dimensions, padding/margins, generic styles, and weight ratios are absent. Expansion counters increment without an explicit current-child reset, which needs subview-update checks. Apply native styles and recompute layout from current children. | Dynamic weighted siblings, removal, zero colors, and style reset work at multiple terminal sizes; padding order matches the shared contract. Dimension units wait for D1. |
| T6 | P1 | TextField advances its model cache before checking editing, suppresses only one Changed message with a boolean, and commits only on submit. Preserve the edit buffer, suppress programmatic messages natively, and commit once on Enter/blur or before click callbacks. | Real typing, programmatic changes, rebinding, normalized model values, Enter, blur, and click-after-edit produce correct event.value and one change callback. |
| T7 | P1 | Checkbox/RadioButton do not refresh labels or invoke click callbacks; programmatic values may emit native change messages. Label/Text ignore selectable; clickable Label changes native widget type. Verify literal text, native focus/keyboard activation, current handlers, and message suppression. | Pilot mouse/keyboard actions invoke the current callback once; removed handlers stop firing; programmatic updates stay silent; markup-like labels remain literal. Selection behavior waits for D2 if native support cannot match it. |
| T8 | P1 | Scroll.scrollX/Y only store offsets; update neither applies nor preserves them. Implement start/end requests, END, user-position preservation, axis policies, and content-growth/resize handling after native layout. | Native scrolling reaches requested start/end positions, retains manual position across unrelated redraws, follows END on growth, and tolerates empty/replaced content. Units wait for D1. |
| T9 | P1 | Tabs rebuilds the tab strip on structural changes, ignores tabposition, and does not refresh labels on ordinary reuse. Preserve keyed page/selection identity and update labels with public APIs. | Mouse/keyboard switching, renaming, reorder, selected-page removal, and empty tabs work without spurious selection resets; unsupported positions are documented. |
| T10 | P1 | ProgressBar scales values but has no explicit range/zero policy. Window discards title and all other parameters. Apply terminal-supported title/progress behavior and audit keyboard event forwarding. | Fractional/range updates and the agreed zero-range indicator work; title changes apply; desktop-only state follows the capability decision in D3. |
| T11 | P1 | Canonical exports and unsupported capability reporting are inconsistent. Add truthful canonical placeholders/aliases and audit the reference matrix and cookbook X flags against native checks. | Common imports and supported examples run; missing features never appear implemented solely because a name exists or a call silently returns None. |
| T12 | P2 | Evaluate native Grid and Rule for Grid/Divider; validate existing Markdown updates and teardown. Implement direct native mappings after lifecycle/layout fixes. | Reactive children/spans, divider orientation, and Markdown content updates pass without new dependencies or custom rendering. |
| T13 | P2 | Evaluate native Select for non-editable ComboBox, reusing shared label/value resolution. Keep editable behavior separate until an appropriate native design is agreed. | Empty choices, invalid indices, duplicate labels/distinct values, model rebinding, and keyed selection match the agreed supported contract. |
| T14 | P3 | Evaluate native DataTable, Tree, screens/dialogs, and remaining desktop/graphics features only after existing components are stable. | Define the supported subset and interaction contract before advertising parity or writing custom editors/renderers. |

The shared DOM currently expresses some moves as remove/add operations. T2 must
first determine whether a backend-local native operation queue can preserve that
contract. If a shared reconciliation API change is necessary, record a concrete
proposal and defer that change for discussion.

## Validation plan

Use `unittest.IsolatedAsyncioTestCase` with Textual's built-in `App.run_test()`
and Pilot. Exercise actual clicks, keyboard input, focus changes, and native
messages; calling PUI callbacks directly is insufficient, as the Flet label
regression demonstrated. Wait for native message/layout processing before
asserting results. No additional test dependency is needed for this harness.
See the [official testing guide](https://textual.textualize.io/guide/testing/).

Add tests/textual_regression.py as work begins. Its intended command is:

```shell
env/bin/python -m unittest discover -s tests -p textual_regression.py -v
```

Validate lifecycle/reconciliation first, then bindings and interactions, then
geometry/scrolling. Include decorated and class subviews, keyed controls, empty
containers, and timer shutdown. Run geometry scenarios at 80x24 and 120x40, with
Unicode/wide text and terminal resize. Check callback count/order, node identity,
native child order, focus, scroll offsets, and absence of PUI error output.

Cycle each cookbook page marked X through the native test app, then operate its
controls. A successful mount is not an interaction test. Finish with a real
terminal check for mouse navigation, keyboard focus, resize, clipping, and exit;
record headless and interactive results separately. Amend cookbook support flags
only when the corresponding behavior has been checked.

## Decisions to discuss

- **D1 — Terminal units and styles:** recommend terminal cells for dimensions,
  padding, and scroll offsets, with no implicit pixel conversion. Define rounding
  and unsupported font size/family behavior before implementing those mappings.
- **D2 — Text interaction:** define selectable text/copy behavior and whether
  clickable labels enter the keyboard focus order; use native facilities and
  retain literal text rather than Rich markup unless explicitly requested.
- **D3 — Window and desktop scope:** recommend one terminal screen with reactive
  title. Decide how size, maximize/fullscreen, menus/toolbars, MDI, Splitter, and
  native interop report unsupported behavior. The shared initial-state versus
  imperative-state contract must not become reactive maximize/fullscreen props.
- **D4 — Editable ComboBox and data views:** agree native composition for free
  text, typed choices, table editing, and tree identity/expansion preservation.
  Do not add bespoke editors merely to mark these components supported.
- **D5 — Modal/dialog API:** Textual screens are asynchronous. Agree result,
  cancellation, and focus restoration semantics before adapting synchronous
  imperative dialog helpers; do not introduce a nested event loop.
- **D6 — Graphics and dependencies:** Canvas, general Image, HTML rendering,
  Matplotlib, and terminal graphics protocols need a defined terminal contract
  and possibly extra dependencies. Leave them explicitly unsupported pending
  agreement; do not create parsers or rasterizers to avoid that discussion.
- **D7 — Shared changes:** consult before modifying the shared DOM move contract,
  drag/drop payloads, or other cross-backend APIs. Continue unrelated work while
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
  Select, Rule, TabbedContent, DataTable, and Tree are candidates to assess, not
  evidence that their full PySide6 contracts already match.
