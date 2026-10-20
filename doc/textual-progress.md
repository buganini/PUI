# Textual alignment plan and progress

Autocomplete validation must follow the [shared acceptance criteria](Reference.html#autocomplete-acceptance); unverified cases remain pending, including real IME and platform-specific focus behavior.

**Pending** items have not been aligned; **Partial** items have the listed gaps.
Existing modules may be partial; their presence is not a completed alignment item.
Runtime checks are **Unverified** until exercised. Remove completed items from
this backlog and keep only outstanding checks/decisions.

## Baseline and process

Use backend `Application`/`PUIView` classes for new code and examples. Keep
deprecated decorators covered by compatibility checks during migration.

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
update this document, [common reference](Reference.html), relevant cookbook flags,
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
tests/layout/textual_scroll.py and layout experiments in refs/textual_layout.py.
Legacy decorator warnings, metadata, and argument forwarding are checked in
[decorator_signatures.py](../tests/decorator_signatures.py). Textual validation
on Python 3.9 remains pending; the separate
[shared/Qt Python 3.9 check](../README.md#python-39-compatibility) does not cover Textual.

Existing modules cover Application/Window, linear layouts, Spacer, Label/Text,
Markdown, Button, Checkbox, RadioButton, TextField, ProgressBar, Scroll, Tabs, Views,
and Table. Stack uses VBox as a reversed vertical fallback; overlapping children are not supported.
Presence does not establish behavioral parity. Canvas and misspelled Combobox
exports are placeholders, Divider returns None, and several canonical component
names are absent. Html explicitly reports unsupported.

## Prioritized work

Source findings identify what to reproduce before changing behavior. The table
lists only outstanding behavior; the Views suite does not validate unrelated modules.

| ID | Priority | State | Finding and planned change | Acceptance check |
| --- | --- | --- | --- | --- |
| T1 | P0 | Pending | Application queues redraws, but TPUIView is empty and the exported PUI decorator uses synchronous shared views. Give Application, decorated views, and class subviews a consistent coalesced native queue, including worker/Timeline requests and removed-view guards. | State changes from clicks, subviews, and a worker update once per burst on the app loop; retired/removed nodes do nothing; quit stops timers. |
| T2 | P0 | Partial | General layout removal outside Views/Tabs still calls Widget.remove() during keyed moves. Audit mount/remove ordering, virtual parents, root replacement, and empty Scroll children. | Insert, reorder, replace, and remove general keyed controls without duplicate mounts, lost focus/edit buffers, orphan widgets, or events reaching removed nodes. |
| T3 | P0 | Partial | Label.postUpdate() repeatedly mounts its existing child. Audit clickable/plain transitions and asynchronous mount/removal boundaries. | Repeated label updates and clickable/plain transitions preserve correct ownership without duplicate mounts. |
| T4 | P0 | Pending | Application has no quit implementation, does not handle native child removal, and assumes every bubbled widget event has puinode. Complete native App.exit()/PUI teardown and guard event ownership/current-node resolution. | Exit through the PUI API and native app shutdown releases timers/views; unrelated native widgets and delayed events do not crash event dispatch. |
| T5 | P1 | Partial | Terminal-only tLayout/tStyle/tsize and t-prefixed visibility bounds are implemented. Expansion counters still increment without an explicit current-child reset, which needs subview-update checks. Broaden fractional-weight and nested scrolling checks. | Dynamic weighted siblings, removal and style reset work at multiple terminal sizes; padding order matches the shared contract. Terminal layout units are whole character cells. Native HBox alignment centers the group; VBox left-aligns children, so mixed-size children may not share a center line; exact per-child centering is outside the current approximate-alignment scope. |
| T6 | P1 | Partial | TextField still commits only on submit. Complete blur/before-click commits and normalized-value handling; broaden rebinding and rapid-update checks. | Model rebinding, normalized values, Enter, blur, and click-after-edit preserve the current edit and produce one change callback. |
| T7 | P1 | Pending | Checkbox/RadioButton do not refresh labels or invoke click callbacks; programmatic values may emit native change messages. Label/Text ignore selectable; clickable Label changes native widget type. Verify literal text, native focus/keyboard activation, current handlers, and message suppression. | Pilot mouse/keyboard actions invoke the current callback once; removed handlers stop firing; programmatic updates stay silent; markup-like labels remain literal. Selection behavior waits for D2 if native support cannot match it. |
| T8 | P1 | Pending | Scroll.scrollX/Y only store offsets; update neither applies nor preserves them. Implement start/end requests, END, user-position preservation, axis policies, and content-growth/resize handling after native layout. | Native scrolling reaches requested start/end positions, retains manual position across unrelated redraws, follows END on growth, and tolerates empty/replaced content. Scroll offset units still need a separate contract. |
| T10 | P1 | Pending | ProgressBar scales values but has no explicit range/zero policy. Window discards title and all other parameters. Apply terminal-supported title/progress behavior and audit keyboard event forwarding. | Fractional/range updates and the agreed zero-range indicator work; title changes apply; desktop-only state follows the capability decision in D3. |
| T11 | P1 | Pending | Canonical exports and unsupported capability reporting are inconsistent. Add truthful canonical placeholders/aliases and audit the reference matrix and cookbook X flags against native checks. | Common imports and supported examples run; missing features never appear implemented solely because a name exists or a call silently returns None. |
| T12 | P2 | Pending | Validate the new shared-placement Grid adapter with large/scrolling content, complex terminal style constraints and platform input behavior; Rule/Divider remains missing. Validate existing Markdown updates and teardown. | Reactive children/spans, divider orientation, and Markdown content updates pass without new dependencies or custom rendering. |
| T13 | P2 | Partial | Select handles non-editable choices; Input plus a non-focusable OptionList overlay handles editable application-defined candidates. Remaining checks: real terminal IME/paste, screen-reader behavior, narrow/edge placement, large lists, duplicate labels, removal/reordering and rebinding during selection. | Follow the shared autocomplete acceptance matrix; Pilot input, keyboard/mouse selection, retained editor, external updates and disabled/completion toggles have coverage. |
| T14 | P3 | Pending | Evaluate native Tree, general screens/dialogs, and remaining desktop/graphics features only after existing components are stable. | Define the supported subset and interaction contract before advertising parity or writing custom editors/renderers. |
| T15 | P2 | Partial | Table lacks cell widgets, drag/drop or header sorting, native column resizing and Qt-style multi-selection. Cell callbacks follow native activation rather than every raw click. | Agree any expanded interaction contract before adding custom gestures or renderers. |
| T16 | P2 | Unverified | Table needs real-terminal mouse/keyboard/focus, resize/clipping, other platforms, large-data and Python 3.9 runtime checks. | tests/textual_table.py covers native headless activation, typed dialogs/choices, cancellation, keyed moves and teardown; exercise cookbook tables in real terminals at multiple sizes. |

The shared DOM currently expresses some moves as remove/add operations. T2 must
first determine whether a backend-local native operation queue can preserve that
contract. If a shared reconciliation API change is necessary, record a concrete
proposal and defer that change for discussion.

## Validation still needed

The broader checks below remain **Unverified**. Views still needs interactive
terminal focus, keyboard traversal, resize and clipping checks. Its headless
suite covers native typing/submit, retained edits, empty selection, State models,
old handles, keyed reorder/removal and independent subview redraws. Run it with
`env/bin/python -m unittest discover -s tests -p textual_views.py -v`.

Tabs still needs broader keyboard/focus, rapid-update and real-terminal layout
checks, including the selection underline after reordering. Its native headless
suite covers mouse clicks, optional models, ID/text matching, duplicate keys,
retained pages, labels, rebinding and empty transitions. Run
`env/bin/python -m unittest discover -s tests -p textual_tabs.py -v`.

Use `unittest.IsolatedAsyncioTestCase` with Textual's built-in `App.run_test()`
and Pilot. Exercise actual clicks, keyboard input, focus changes, and native
messages; calling PUI callbacks directly is insufficient, as the Flet label
regression demonstrated. Wait for native message/layout processing before
asserting results. No additional test dependency is needed for this harness.
See the [official testing guide](https://textual.textualize.io/guide/testing/).

[tests/textual_regression.py](../tests/textual_regression.py) covers Button,
Checkbox and RadioButton activation blocking through disabled toggles, TextField sizing, and buffered
editor mounting. Placeholder updates, initially empty input, and programmatic
changes also have headless coverage. Real-terminal hint appearance and
disabled-control focus traversal remain unverified. Run it with:

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

Check application terminal titles on native macOS/Windows and terminal emulators
with title changes disabled. Prior-title restoration and reactive title binding
are not implemented; Window.title still has no terminal effect.

## Decisions to discuss

- **D2 — Text interaction:** define selectable text/copy behavior and whether
  clickable labels enter the keyboard focus order; use native facilities and
  retain literal text rather than Rich markup unless explicitly requested.
- **D3 — Window and desktop scope:** recommend one terminal screen with reactive
  title. Decide how size, maximize/fullscreen, menus/toolbars, MDI, Splitter, and
  native interop report unsupported behavior. The shared maximize/fullscreen
  contract is initial-only, with equivalent constructor arguments and declarative
  setters; do not introduce reactive props or imperative state methods.
- **D4 — Data views:** agree tree identity/expansion preservation; table interaction
  extensions are tracked in T15. ComboBox acceptance gaps are tracked in T13.
- **D5 — General Modal/dialog API:** Textual screens are asynchronous. Agree result,
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
  Rule, TabbedContent, and Tree are candidates to assess, not
  evidence that their full PySide6 contracts already match.
