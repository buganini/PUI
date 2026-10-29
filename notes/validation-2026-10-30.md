# Backend QA evidence and follow-ups — 2026-10-30

Collected from progress notes while separating completion from test coverage.
This is not a new test run. Existing dates, environments and results are preserved;
unrun checks remain unrun. Implemented integrations are complete regardless of
these follow-ups. Record the OS/runtime/browser when adding actual results; do not
assume an unspecified environment or infer a pass from an implementation.

See also [2026-10-28 runtime audit](validation-2026-10-28.md).

## wx

### Validation still needed

| Area | State | Pending check |
| --- | --- | --- |
| macOS custom colours | Partial | A 32-shared-page dark-appearance Cookbook pass against PySide6 checked explicit colours; pixel tests cover compact Label backgrounds and parsed HTML default/inline colours. Non-selectable Label/Text with explicit backgrounds and explicitly coloured Buttons use generic painting; entering/leaving these styles remounts the control. Verify keyboard/accessibility, light appearance, other DPI settings and arbitrary colours on remaining native controls. |
| Cookbook geometry parity | Unverified | Revisit the earlier Cookbook visual differences after the shared Grid priority/span fixes. macOS Grid sizing regression passes; Adaptive Grid visual parity, Canvas explicit-size expansion, Splitter proportions and clipping of long examples still need focused visual checks. |
| TextField placeholder | Unverified | Focus-dependent hint appearance on other platforms; native tests cover hint updates/removal, cursor/edit retention, and binding events |
| ComboBox autocomplete | Partial | Non-grabbing candidate popup has Linux GTK input/selection coverage, including State-bound Cookbook typing through relayout; open candidates follow editor and ancestor geometry after layout instead of closing on size events. Linux Cookbook window resizing and Escape/continued typing are checked. Validate real IME composition, macOS/Windows, theme/DPI and parent scrolling. The ordinary arrow dropdown retains native behavior. |
| Disabled controls | Unverified | Native mouse/keyboard focus behavior across platforms; tests/wx_regression.py covers disabled toggles, retained Button/ComboBox/Checkbox/RadioButton controls, and preserved values/editability |
| Views | Unverified | Manual focus/keyboard transitions and other platforms; selection, retained edits, keyed moves/removal and model replacement are covered by tests/wx_views.py |
| Tabs | Unverified | Broader keyboard/focus and platform behavior; optional models, native selection events, duplicate keys, keyed moves, labels and empty transitions are covered by tests/wx_tabs.py |
| Splitter | Unverified | Manual sash dragging/double-click behavior, minimum sizes at display scaling, and other platforms; native ownership, geometry, resize, redraw, keyed moves and subview updates are covered by tests/wx_splitter.py |
| Tree | Unverified | Manual mouse/keyboard interaction, column sizing on other platforms, and broader platform behavior; native model, hit-testing, selection/expansion and reconciliation tests are in tests/wx_tree.py |
| Table | Unverified | Manual keyboard/mouse editing, selection and scrolling on other platforms; native Grid/editor regression tests are in tests/wx_table.py |
| Dialogs | Unverified | Operate native file/directory, message, and input dialogs; verify cancellation/results |
| Canvas input | Unverified | Exercise native press/release, drag, hover, double-click, wheel coordinates/modifiers, and removal during input |
| Canvas rendering | Unverified | Six native Canvas tests now pass on macOS Cocoa as well as Linux GTK. Broaden Windows rendering, HiDPI and HeavyCanvas throughput checks; measure native 120,000–1,000,000-session presets and memory use; Linux GTK mixed primitives and nested Shapely holes are covered by tests/wx_canvas.py |
| Tabs/layout | Unverified | Check HBox vertical centering and VBox left alignment and native minimum-size behavior on other platforms and display scales; Linux GTK resize/redraw and retained editor expansion are covered. Compare notebook placement with PySide6 |
| Display/platforms | Unverified | Check display scaling, other platforms, and broader cookbook interactions beyond the Table/Views switching regression in tests/wx_views.py |

Existing regression suites: [wx_canvas.py](../tests/wx_canvas.py), [wx_regression.py](../tests/wx_regression.py) and
[timeline_regression.py](../tests/timeline_regression.py), plus
[wx_table.py](../tests/wx_table.py), [wx_tree.py](../tests/wx_tree.py), and
[wx_splitter.py](../tests/wx_splitter.py), and [wx_views.py](../tests/wx_views.py). The recorded runtime
includes wxPython 4.3.1 / wxWidgets 3.3.3 on Linux GTK (earlier checks used 4.2.4 / 3.2.9).
On 2026-10-27, macOS Cocoa with Python 3.14.8, wxPython 4.3.2 / wxWidgets 3.3.4
passed `wx_table` and `grid_sizing.NativeGridSizing.test_wx` (8 tests).
These automated checks do not replace manual OS input/accessibility checks. Run
`python3 -m unittest discover -s tests -p 'wx_*.py' -v` and
`python3 -m unittest discover -s tests -p timeline_regression.py -v`.
Passing those checks does not complete the pending native checks above.
Legacy decorator warnings, metadata, and argument forwarding are checked in
[decorator_signatures.py](../tests/decorator_signatures.py). Native wx validation
on Python 3.9 remains pending; the separate
[shared/Qt Python 3.9 check](../PUI/doc/pyside6-reference.md#python-39-compatibility) does not cover wx.

#### Visibility and adaptive layout

- **Unverified:** macOS/Windows focus handling when `.visible(False)` hides the focused control; Linux retained-control toggling is covered by regression tests.

Adaptive Layout: content-size observations, retained State and threshold transitions have Linux regression coverage; macOS/Windows theme, DPI and nested scrolling geometry checks remain.

#### Divider validation

Divider native tests passed on macOS Cocoa (2 tests, 2026-10-28); Windows and
external theme/DPI validation remain. Linux GTK checks cover HBox/VBox resizing, virtual views and direct
HVBox/VHBox direction changes in [divider_native.py](../tests/divider_native.py).

### HTML WebView

Html now prefers WebView (WebKit on macOS/Linux, Edge WebView2 on Windows).
Unavailable engines/imports or synchronous creation failure emit RuntimeWarning
and fall back to HtmlWindow; ordinary page/resource load errors do not. CSS
font/colour defaults and selectable are applied; unchanged content is retained.
WebView uses viewport sizing, not HtmlWindow's intrinsic content-size hint.
macOS WebKit CSS, content retention and forced fallback tests pass. Windows
WebView2 and Linux WebKit runtime availability still require native validation.

### Declarative Modal

Uses wx.Dialog.Show() and the shared state-driven Modal lifecycle without a
nested event loop. A per-application modal stack disables other visible windows,
preserves already-disabled windows and restores input/focus on close. Ancestors
are ordered below descendants even when reconciliation opens the child first.
Native macOS tests cover retained content, Escape/close binding updates,
parent close/reopen, removal and native parent destruction. Windows/Linux remain
to be validated. Use a layout container for multiple children; Frame-specific
menus/status bars are outside the Dialog content contract.

### Additional QA scenarios

- **Canvas text portability**: macOS native pixel tests cover nine anchors, fractional point sizes, multiline spacing, rotated width/height clipping, alpha and state restoration (tests/canvas_text.py). Repeat on Linux/Windows with their native fonts/renderers
- **Stack**: Windows Cookbook text layer order visually checked at normal/maximized sizes with wxPython 4.3.2 / wxWidgets 3.3.4 after declaration-order text composition fix; pixel tests cover text layer order, reorder, hide/show and resize. Verify keyboard focus, pointer hit testing, mixed native controls and macOS transparency. Linux geometry, resize, keyed reorder and removal and Windows retained text updates/reorder have regression coverage
- **Modal**: Non-blocking Dialog, managed application modality and retained content; native macOS tests pass, Windows/Linux need validation
- **Table portability**: Recheck decorated editor focus, keyboard commit/cancel and choice handling on Linux/Windows. The editor now uses wx.Control (or the native field directly), not wx.Panel; macOS wxPython 4.3.2 passes tests/wx_table.py. This does not verify every 4.3 release/platform.

## tkinter

### Validation still needed

Menu creation and invocation, nesting, updates, reorder/removal and Tcl callback
cleanup pass on macOS Tk 9.1, including cookbook callbacks. Windows/Linux menu
placement and interactive keyboard navigation remain unverified.
The 2026-10-29 macOS Tk 9.1 regression run passed 74/77 existing Tk tests:
two fullscreen-exit assertions and the Combobox test's hard-coded `.popdown.f.l`
path failed identically with the committed Window implementation. These remain
platform/test compatibility follow-ups, separate from menu support.

| Area | State | Pending check |
| --- | --- | --- |
| Disabled controls | Unverified | Broader mouse/keyboard focus and platform behavior; tests/tkinter_regression.py covers Button/Checkbox/RadioButton activation blocking and ComboBox value/editability retention through disabled toggles |
| Views | Partially verified | Fixed early ancestor refresh reaching pages before their native widgets mount. All four tests now pass on macOS Tk 9.1, covering selection, retained edits, keyed moves/removal and model replacement. Manual focus/keyboard transitions and Windows remain pending |
| Tabs models | Unverified | Broader keyboard/focus and platform behavior; native selection events, optional models, duplicate keys, keyed moves, labels and empty transitions are covered by tests/tkinter_tabs.py |
| Scroll | Unverified | Exercise resize, END following, content growth, user-position preservation, and local wheel behavior |
| Dialogs | Unverified | Operate native dialogs; current helper tests check argument/result conversion |
| Table | Unverified | Manual keyboard/focus, column resizing/scrolling, display scaling, other platforms and large-data performance. tests/tkinter_table.py covers native rows, typed dialog edits/choices, callbacks, redraws, keyed moves, delayed dialog visibility, cancellation before display and teardown |
| Window | Unverified | Broaden native state/close checks on other window managers/platforms and multi-window modal focus. tests/tkinter_lifecycle.py covers last-window exit, retained other windows, replacement/removal, and dialog/timer/redraw cleanup |
| Divider | Unverified | Three native macOS Tk 9.1 tests pass; Windows and external themes remain unchecked. Linux HBox/VBox resizing, virtual views, direct HVBox/VHBox direction changes and installed clam/alt/default/classic themes are covered by tests/divider_native.py |
| Layout/Tabs | Unverified | Compare geometry, resizing, and ttk tab placement with PySide6 |
| Canvas | Unverified | Three native Canvas tests pass on macOS Tk 9.1. Broaden Windows, font/theme repaint and performance checks; measure item recreation and memory use with the native 120,000–1,000,000-session presets; tests/tkinter_canvas.py covers per-paint default refresh, native item recreation and style cleanup after errors on Linux Tk 8.6 |
| Display/platforms | Unverified | Check display scaling, other platforms, and broader cookbook interactions, including the cookbook's use of the external Sun Valley light theme |

Theme coverage: [tkinter_themes.py](../tests/tkinter_themes.py) checks all implemented widget families across installed themes. macOS Tk 9.1 was checked with aqua, clam, alt, default and classic; Linux Tk 8.6 was checked with clam, alt, default and classic. Windows rendering and third-party themes still need runtime verification. The macOS fullscreen-exit timeout also occurs with the original backend.

Sizing policy coverage: [tkinter_sizing.py](../tests/tkinter_sizing.py) checks nested container expansion, sibling priority, explicit weight ratios and redraw updates against doc/Layout.html.
On 2026-10-27, `tkinter_sizing` and `grid_sizing.NativeGridSizing.test_tk`
passed 9 tests on macOS / Python 3.14.8 / Tk 9.1.0. Other themes, Windows and
manual focus/input still require their own checks.

Existing suites: [tkinter_regression.py](../tests/tkinter_regression.py),
[tkinter_views.py](../tests/tkinter_views.py), [tkinter_table.py](../tests/tkinter_table.py),
and [tkinter_lifecycle.py](../tests/tkinter_lifecycle.py).
Constructor argument compatibility is checked by
[signature_regression.py](../tests/signature_regression.py); native layout and
platform checks above remain pending.
Run `env/bin/python -m unittest discover -s tests -p 'tkinter_*.py' -v`.
The latest local sizing check used Python 3.14.8 and Tk 9.1.0; earlier
Linux Canvas coverage used Tk 8.6. Canvas cookbook coverage skips cubic drawing.
Passing the suite does not complete the pending native checks above.
Legacy decorator warnings, metadata, and argument forwarding are checked in
[decorator_signatures.py](../tests/decorator_signatures.py). Native Tk validation
on Python 3.9 remains pending; constructor/decorator checks in the separate
[Python 3.9 baseline](../PUI/doc/pyside6-reference.md#python-39-compatibility) do not cover native Tk behavior.

#### Visibility and adaptive layout

- **Unverified:** macOS/Windows focus handling when `.visible(False)` hides the focused control; Linux retained-control toggling is covered by regression tests.

Adaptive Layout: content-size observations, retained State and threshold transitions have Linux regression coverage; macOS/Windows theme, DPI and nested scrolling geometry checks remain.

### Declarative Modal

Uses a retained transient Toplevel with a native grab, Escape/close binding
updates and open/close callbacks. macOS tests cover retained content, removal,
nested grabs and parent close/reopen. Windows/Linux interactive validation
remains pending.

### Additional QA scenarios

- **Linear alignment**: HBox/VBox use sibling-local main-axis priorities and vertically center compact HBox children and left-align compact VBox children. Broaden platform checks for explicit dimensions and native size limits
- **ComboBox autocomplete**: Application-declared suggestions retain editor focus through sibling relayout on Linux; native Tcl dropdown focus is handled without Python widget lookup. Validate real IME composition, macOS/Windows, theme/DPI, parent scrolling and window movement. The ordinary ttk arrow dropdown retains native focus behavior.
- **Modal portability**: Implemented; broaden native focus/grab validation to Windows/Linux
- **Splitter portability**: Linux ttk.Panedwindow geometry, visible-content hit-testing, retained sashes/editors, reorder/removal, orientation changes and independent child-view updates pass. macOS Tk 9.1 also passes the two Splitter tests. Windows, other themes and sustained nested resizing remain unverified
- **Stack**: Frame/grid/lift implemented; macOS/Windows focus, hit testing and theme checks remain. Linux geometry, stacking order, resize and keyed reconciliation are tested

## flet

### Validation still needed

- Menus: Flet 1.0.4 Session tests cover nested controls, serialization, retained
  updates, reorder/removal, stale callbacks and cookbook callbacks. Verify actual
  Flutter pointer/keyboard navigation, popup positioning and dismissal.

- TextField placeholder: live-client empty/focused hint appearance; Session
  tests cover hint updates/removal, native overrides, retained edits, and bindings.
- Disabled controls: live-client pointer/keyboard and focus behavior for Button,
  ComboBox, Checkbox and RadioButton; Session tests cover disabled properties, retained controls and
  values, and adding/removing native disabled overrides.
- Tabs: desktop-client keyboard/swipe behavior, broader rapid-change cases and
  focus retention. Browser clicks and both cookbook selection paths were checked;
  tests/flet_tabs.py covers serialized models, click/change events, duplicate keys,
  labels, keyed moves, rebinding and empty transitions.
- Canvas input: desktop-client/platform coverage, touch cancellation, right-button
  dragging.
- Canvas performance: broaden retained-frame Paint sharing checks to desktop
  clients/platforms and measure shape construction, Flet diff/serialization and
  Flutter drawing separately; style reuse does not remove the full shape rebuild.
  Measure throughput and memory for the native 120,000–1,000,000-session presets.
- Standalone Scroll: actual START/END scrolling, user-position preservation,
  content growth, and native axis behavior.
- Table: native double-click/keyboard ordering; Session tests only verify
  double-tap callback routing.
- Broader visual and interaction coverage for the supported cookbook pages;
  serialized Session checks do not establish client rendering correctness.
- Display scaling and other desktop platforms.

Existing regression commands are in [flet_regression.py](../tests/flet_regression.py),
[flet_table.py](../tests/flet_table.py), [flet_canvas.py](../tests/flet_canvas.py),
and [flet_tabs.py](../tests/flet_tabs.py). Run all with
`env/bin/python -m unittest discover -s tests -p 'flet_*.py' -v`.
Worker-thread tests need normal process socket access for asyncio executor cleanup.
Constructor argument compatibility is checked by
[signature_regression.py](../tests/signature_regression.py); client rendering
and interaction checks above remain pending.
Legacy decorator warnings, metadata, and argument forwarding are checked in
[decorator_signatures.py](../tests/decorator_signatures.py). Flet 1.0.4 requires
Python 3.10+; Python 3.9 is outside this backend's supported runtime.
On 2026-10-27, `flet_regression` and `flet_tabs` passed 32 recording-session tests
on macOS / Python 3.14.8 / Flet 1.0.4. This does not validate native Flutter geometry,
focus, touch or screen-reader behavior. Shared
changes must still pass the [Python 3.9 baseline](../PUI/doc/pyside6-reference.md#python-39-compatibility).

#### Visibility and adaptive layout

- **Unverified:** real Flutter-client focus/cursor/scroll behavior after `.visible(False)` then reappearance. Python control/shell retention is tested; transient client state is not guaranteed.

Adaptive Layout: `on_size_change` wiring and inherited size State are covered by the recording-session tests; verify initial geometry and repeated breakpoint transitions in a real Flutter client.

### Declarative Modal

Uses a retained AlertDialog in Page.overlay. State transitions, offValue,
open/close callbacks, removal and serialization are covered by Python tests.
Native macOS open, content-button close, callbacks and reopen passed on 2026-10-28.
PUI now routes Page Escape events to the topmost declarative Modal, while an active
imperative dialog/picker protects underlying modals. Native macOS Flet 1.0.4 checks
on 2026-10-30 passed Escape with TextField focus, reopen, nested inner-first
dismissal and return to the outer modal. Session tests cover offValue, retained
updates, callback counts, ancestor hiding, removal and the imperative-dialog guard.
Windows/Linux Escape and exact focus restoration targets remain unverified.

### Additional QA scenarios

- **HBox / VBox / HVBox / VHBox reversal**: inverse/inverseH/inverseV order and Row/Column switching are tested with the recording transport; Native macOS HBox reversal was visually verified on 2026-10-28. Verify VBox/HVBox/VHBox geometry and cursor/scroll behavior; a combined Modal/reversal sequence showed an empty editor despite retained bound text and needs an isolated reproduction. Client-only state resets on Row/Column replacement are an accepted limitation documented in the reference
- **VBox alignment**: Native Column START and Row CENTER match the alignment defaults; verify client geometry and expansion
- **Imperative dialogs**: AlertDialog messages and desktop FilePicker are implemented; real Session tests cover synchronous results, serial callbacks, cancellation and shutdown, with picker responses mocked. macOS Prompt acceptance, filtered OpenFile path return and closing the app during Prompt were verified on 2026-10-30. Verify remaining native picker modes, Windows/Linux UX and AlertDialog focus/Escape. Flet browser/mobile file helpers remain unsupported because they do not provide desktop paths

## textual

### Validation still needed

On 2026-10-27, `textual_views` and `textual_grid` passed 6 native headless tests
on macOS / Python 3.14.8 / Textual 8.2.8. They cover retained editor/subview behavior
and Grid priorities/spans/breakpoints; they do not validate real terminal input.

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

### Declarative Modal

Uses an installed ModalScreen with contents mounted on first opening and
retained across close/reopen. Headless tests cover Escape, nested screens,
parent close/reopen, retained updates, removal and declaration inside Grid.
Use tLayout for terminal dimensions; pixel size is not applied.

### Additional QA scenarios

- **T16**: Unverified — Table needs real-terminal mouse/keyboard/focus, resize/clipping, other platforms, large-data and Python 3.9 runtime checks. — tests/textual_table.py covers native headless activation, typed dialogs/choices, cancellation, keyed moves and teardown; exercise cookbook tables in real terminals at multiple sizes.
- **T17**: Unverified — Splitter needs real-terminal mouse-protocol, native macOS/Windows, nested/scrolling content and extreme-size checks. — Pilot covers captured dragging, arrow-key resizing, retained editor, orientation/reorder/removal, hidden/empty panes and independent child-view updates; repeat in real terminals.

## web

### Lifecycle validation still needed

Further checks are needed for multi-hour connection/expiry/shutdown races and
descriptor/memory soak tests across larger application workloads. The repeatable
finite harness is `tests/web_soak.py`; measured results belong in the reference.
Include indefinitely retained (`session_ttl=0`) workers in multi-hour resource
and capacity checks, including concurrent renewal/logout and worker admission/cleanup.
Validate the browser's Resume/Renew session choice, auth-only Logout and keyboard focus with
Firefox/Safari, screen readers and mobile connection suspension; prolonged
waiting at the choice banner across real worker expiry still needs device checks.
Validate login autofill/password managers and browser-session cookie behavior
on Firefox/Safari/mobile, including cross-tab logout, offline tabs, stale resume
IDs after gateway restart/re-login and browser back/forward restoration.
Administrative account-wide revocation, global auth-callback concurrency limits
and global login rate limits remain unimplemented. Expired authenticated owner
records are retained outside the anonymous LRU and need a bounded retention policy.
Handshake connection limits and a smaller hello decoding budget still need
implementation. Validate same-account reauthentication/resume UX across mobile,
Firefox/Safari and multiple tabs, including cookie rotation during active requests.
Portable server/IPC tests passed on native macOS on 2026-10-28; repeat on Windows. Linux exercises
both forkserver and spawn, but cannot validate Windows socket-handle transfer,
Proactor I/O, platform console interrupts or native process-handle counts.
Validate interpreter/app packaging separately; frozen executables are unverified.
Remote/container proxy deployments still need end-to-end checks with explicitly
configured IP/CIDR/Unix-socket trust, public ports and their actual network topology.
Verify that deployed proxies preserve the application/login anti-framing headers;
Firefox/Safari checks of browser-enforced framing rejection remain outstanding.

### API integration still needed

The current intermediate contract and unimplemented capabilities are in [web-api.md](../PUI/doc/web-api.md). It defines
bootstrap/framing, message envelopes, server-generated patches, snapshot recovery,
object-ID bindings, ordered edits/events, Canvas commands, resource lifetime and
flow control.
Only the advertised capabilities are enabled; the remaining protocol sections
do not imply support for those widgets.

- Run shared malformed-frame/message fixtures on Firefox/Safari and measure
  decoder limits there; add schemas with new Canvas/resource capabilities.
- Extend binding lifetime checks to long-running registration churn.
- Validate native desktop/mobile IMEs, focus retention across browser engines,
  and widget geometry/Stack overlay hit-testing on other engines. Repeat the
  Chrome recovery and TimelineView update scenarios there.
- Stress long-running application callbacks and image decode/cache churn beyond
  the finite DOM, IPC and image regression checks.
- Validate Canvas pointer capture on native touch devices and other browser
  engines. Validate image loading, format support, resampling and memory peaks
  across other browser engines and larger workloads.
- Verify per-frame Canvas style reuse and native invalid-style fallbacks in
  Firefox/Safari; Chrome pixel comparisons cover the shared renderer.

### Layout validation still needed

Use the [shared layout policy](https://buganini.github.io/PUI/doc/Layout.html)
and [Web layout reference](../PUI/doc/web-reference.md#layout-and-sizing) as the current
contract, including the 0–5 priorities, inherited container demand and Grid track
allocation and the backend-specific dimension behavior documented in the reference.

On 2026-10-27, `tests/browser_grid_sizing.cjs` passed in macOS Chrome, including
compact tracks, both axes, weights, spans, visibility, resize and retained editors.
`tests/browser_grid_alignment.cjs` also passed label/input centering, multiline
labels, spans, selection and reparenting checks.
This is shared-renderer coverage, not a Pyodide bridge or cross-engine result.

Repeat `tests/browser_expansion.cjs`, `tests/browser_grid_sizing.cjs`,
`tests/browser_grid_fill.cjs`, `tests/browser_grid_alignment.cjs` and
`tests/browser_adaptive.cjs` scenarios on Firefox/Safari and devices. Check
content-sized tracks, spanning cells, nested containers, explicit dimensions,
retained updates and viewport resizing. Chrome coverage does not establish
cross-engine geometry parity or identical native font/theme metrics.

#### Drop validation still needed

Inbound file/text/URL drops have automated browser coverage. Real OS file-manager drags across Safari/Firefox and mobile file sources remain unverified. Directory drops, outgoing drag sources and table row reordering are not supported.

Container-size observations and adaptive bounds still need Firefox/Safari and mobile resize checks, including reconnect during resizing and content-dependent layout feedback. Chromium content-box measurement, threshold transitions and shared input retention are covered.

### Declarative Modal

Uses native HTML dialog.showModal(), with retained DOM content, Escape/close
actions, focus restoration, nested dialogs and stale dismissal rejection.
Browser tests exercise the native dialog behavior.

### Menu validation

MenuBar/Menu/MenuAction share the browser navbar renderer. Chromium tests cover
nested popovers, keyboard navigation, outside dismissal, retained reorder/updates,
hiding/removal and content sizing. Both cookbook builds were exercised through
actual Web/Pyodide transports. Firefox, Safari, touch and assistive-technology
navigation remain unverified; dropdowns require the native Popover API.

### Open file helpers (2026-10-29)

OpenDirectory/OpenFile/OpenFiles combine device upload and server browsing. Files
support drag/drop; folders require explicit picker selection and cannot preserve
empty directories. HTTP upload batches are scoped to the active dialog and epoch,
streamed to disk, and cancelled on dialog completion/disconnect. Unit/IPC tests
cover path validation, quota storage, cancellation and cleanup in isolated and
passthru modes. Chrome tests cover actual file/folder selection, file drops, server
multi-selection and retained browsing. Firefox/Safari/mobile remain unverified.

### Additional QA scenarios

- **W1**: Firefox/Safari framing and message validation — Run the shared malformed fixtures and current dispatch checks on additional browser engines; D3
- **W2**: Multi-hour/application lifecycle soak checks — Extend the finite harness to long-running descriptor/memory and expiry/shutdown workloads
- **W4**: Native IME and cross-engine focus/recovery validation — Real input methods and recovery behavior on browsers beyond Chrome; MaskedField password-manager/autofill and mobile keyboard behavior; custom ComboBox candidate listbox positioning, editor focus retention and keyboard/mouse selection across browsers/devices, following the shared autocomplete acceptance criteria and cookbook
- **W5**: Cross-engine layout validation — Repeat the Chrome geometry checks on Firefox/Safari and devices: Grid priority allocation, spans, nested demand, cell fill and vertical alignment; HBox vertical centering, VBox left alignment, Tabs header overflow/focus and Splitter pane retention/dragging/keyboard behavior. Splitter real touch remains unverified; D3
- **W8**: Image portability and resource stress checks — Firefox/Safari formats, resampling, animated images, long-running cache churn, decode memory peaks and rapid file-replacement races
- **W12**: Native macOS/Windows and broader installed-package validation — macOS portable server/IPC, Unix socket ownership/permissions/cleanup, startup, stop and SIGTERM tests pass (2026-10-28). Verify Windows Proactor I/O, console Ctrl-C, process/handle soak tests and installed wheel assets. Windows named-pipe listeners remain unavailable; use TCP binds. Linux exercises forkserver and spawn; remaining Windows checks and frozen executables remain unverified
- **W14**: Accessibility and application/browser performance validation — Screen readers, CPU/RSS near the five-million-item budget, full-batch serialization, snapshot construction, structural index and browser budget costs, long-lived retained-index/shared-record/budget-cache/compression-stream memory with the 4 MiB history window, browser/network latency, sustained Canvas throughput near the 300,000-command/aggregate limits on desktop and mobile; use the seeded [HeavyCanvas cookbook](../PUI/cookbook/heavycanvas.py) for repeatable 1,000–30,000-session workloads, including wheel zoom with large coordinate replacements versus small hover updates; native touch/pen and Firefox/Safari checks of per-command drawing-error recovery, Canvas splices/recovery and uncoalesced mousemove input and presentation-gated repaint coalescing remain

## pyodide

### Validation scope

On 2026-10-27, `tests/pyodide_bootstrap.cjs` passed against the locally built
static cookbook in macOS Chrome with the actual CDN-loaded Python worker:
CDN failure reporting, archive mismatch recovery, retry, fresh reload and
independent tabs. The test explicitly selects its page instead of relying on
the cookbook's default page, and distinguishes navigation from demo buttons.
`pyodide_runtime` also passed 9 CPython tests; those do not execute WebAssembly.

The public [GitHub Pages cookbook](https://buganini.github.io/PUI/cookbook/cookbook.html)
was also checked on 2026-10-27 in macOS Chrome: the Python worker loaded and
clicking B on the Button page updated State and the displayed label. The public
Reference.html and Layout.html URLs both returned HTTP 200. Deployment is not
an outstanding task.

The full interaction/IME matrix, Firefox/Safari and long-running memory behavior
still require the specific checks listed in Y5–Y10.

### Performance measurements still needed

Use HeavyCanvas's 1,000–30,000-session presets, including hover and broad zoom
changes. Measure cold and warm CDN loads separately; a single startup time is not
a cold-download benchmark. Record browser/device, viewport, DPR and sample count.

Separate painter execution, snapshot collection, structural indexing/diff, Python-to-JS
conversion/null normalization, structured cloning, DOM apply and Canvas replay.
Measure command-tuple construction and the 128-entry integer-color LRU in
the actual Pyodide worker; native CPython timings do not establish the WebAssembly
performance improvement.
Use correlation IDs and context-local timing, reporting median and tail latency.
Track live resources and retained memory during repeated updates. Compare local
structured cloning with MessagePack/transferable buffers before proposing a binary
bridge; neither approach is automatically zero-copy.

#### Drop validation still needed

Inbound file/text/URL drops have automated browser coverage. Real OS file-manager drags across Safari/Firefox and mobile file sources remain unverified. Directory drops, outgoing drag sources and table row reordering are not supported.

Adaptive Layout: the shared browser ResizeObserver and Python local-bridge size messages are tested separately; verify the combined path in the CDN-backed runtime and across browser engines.

Splitter: shared-renderer mouse/keyboard, nesting and pane-retention checks pass
in Web Chromium. Repeat them through the actual Pyodide bridge and other engines.

### Declarative Modal

Uses the shared browser renderer and native HTML dialog.showModal(). Content
is retained across close/reopen; Escape and close actions update the binding.
Native browser focus and nested dialogs are covered by the shared renderer tests.

### Menu validation

MenuBar/Menu/MenuAction share the browser navbar renderer. Chromium tests cover
nested popovers, keyboard navigation, outside dismissal, retained reorder/updates,
hiding/removal and content sizing. Both cookbook builds were exercised through
actual Web/Pyodide transports. Firefox, Safari, touch and assistive-technology
navigation remain unverified; dropdowns require the native Popover API.

### SaveFile downloads (2026-10-29)

SaveFile uses JSPI/run_sync for synchronous filename selection, then returns a
worker-local temporary path. The shared download shelf polls visible IDs through
the local worker bridge and delivers Blob downloads. Real Chrome validation covers
cancel/Escape, invalid filenames, exact output bytes, notification dismissal,
polling stop and Blob URL cleanup. Browsers without JSPI cannot use this synchronous
helper; Firefox/Safari execution remains unverified. No server filesystem picker,
HTTP download endpoint or SharedArrayBuffer dependency is introduced.

### Generic imperative dialogs (2026-10-29)

SaveFile and Information/Warning/Critical/Confirm/Prompt now share the dialog/reply
bridge with request IDs and worker epochs. Chrome browser tests cover all five
helpers, sequential calls, Escape, confirmation, empty/default prompt values,
and the existing SaveFile download lifecycle. JSPI is required; other-browser
validation remains pending.

### Open file helpers (2026-10-29)

OpenDirectory/OpenFile/OpenFiles now share the dialog UI and UploadStore with Web.
File selection and file drops import copies into the virtual filesystem. Folder
selection preserves relative paths; folder drops and empty-directory preservation
are unsupported and explicitly labeled. JSPI remains required. Other-browser
validation remains pending.

### Additional QA scenarios

- **Y5**: Native control and selection suites pass; the full Web geometry, IME and stale-binding matrices have not all been rerun through Pyodide. — Run native browser interaction/resize cases, including mixed fixed/flexible sizing and composition.
- **Y6**: Tabs/Views/Table use shared implementations; malformed/stale list/dict binding and editor-lifetime coverage still needs the actual Pyodide bridge. — Repeat binding invalidation and delayed-input cases in the worker, beyond shared Python regression coverage.
- **Y7**: HeavyCanvas hover, zoom and command deltas are exercised; cross-engine Canvas style reuse/invalid-command handling, long-running continuous painters, synthetic backpressure and prolonged background-tab behavior remain unverified. — Bounded queues/resources and matching revisions after repeated foreground/background changes and resize.
- **Y8**: Bundled Image works; local Canvas image crop/scale, failed decode and sustained image-revision churn need browser coverage. — No stale Blob URL access or leak while decode, remove, replace and restart overlap.
- **Y10**: Firefox, Safari/mobile browsers and memory/proxy soak tests are unverified. — Check module-worker loading, native controls, long callbacks, background lifecycle and repeated teardown on those browsers.

## Additional QA context

### wx: additional QA context

sizer-only targets, outgoing drags and real OS cross-platform drag validation remain

### tkinter: additional QA context

Native text dimensions round pixel requests up to whole characters/lines; verify theme/DPI and macOS/Windows rounding. Axes without native sizing options remain unsupported

### flet: additional QA context

Touch, native macOS/Windows and long-running nested/scrolling panes remain unverified.

### flet: additional QA context

; verify Flutter focus, gesture timing, scrolling and native geometry

### flet: additional QA context

- Imperative dialogs: verify native focus/Escape and platform-specific picker behavior; Linux requires Zenity.

### flet: additional QA context

- Real IME composition, screen readers, touch/mobile and macOS/Windows.

### flet: additional QA context

- Flet Web runtime interaction checks for the integrated control; the native Linux
  Cookbook checks do not establish browser coverage.

### flet: additional QA context

Remaining checks/gaps:

### flet: additional QA context

sustained redraw performance. Test platform-native appearance on Windows/Linux;
macOS native smoke tests and shared browser pixel tests do not prove all platforms.

### flet: additional QA context

Native Flutter
keyboard/focus behavior still needs interactive validation.

### web: additional QA context

sustained redraw performance. Test platform-native appearance on Windows/Linux;
macOS native smoke tests and shared browser pixel tests do not prove all platforms.

### web: additional QA context

Native Flutter
keyboard/focus behavior still needs interactive validation.

### pyodide: additional QA context

sustained redraw performance. Test platform-native appearance on Windows/Linux;
macOS native smoke tests and shared browser pixel tests do not prove all platforms.

### pyodide: additional QA context

Native Flutter
keyboard/focus behavior still needs interactive validation.

### flet: additional QA context

The macOS desktop client mounted the six-panel chart and reported Canvas dimensions,
but Canvas.capture() timed out. A separate native macOS line chart was visually verified on 2026-10-28; the six-panel output comparison remains pending. Python
shape construction and serialization regressions pass. Do not treat this as a
completed native screenshot comparison.

### pyodide: additional QA context

Cross-engine and assistive-technology validation remains pending.

### textual: completed integration QA

- **T5**: Broaden tWideVisible cell-width boundary checks for real terminals and deeply nested/scrolling parents; shared-boolean inheritance, explicit overrides and retained hidden children have regression coverage. Broaden fractional-weight and nested scrolling checks. Verify inherited color/background/weight changes in real terminals and themed composite controls, including resize across tWideStyle breakpoints. Coverage/checks: Dynamic weighted siblings, removal and style reset work at multiple terminal sizes; inspect rendered text colors/weight as well as style properties. Padding order matches the shared contract. Terminal layout units are whole character cells. Native HBox alignment centers the group; VBox left-aligns children, so mixed-size children may not share a center line; exact per-child centering is outside the current approximate-alignment scope.

### textual: completed integration QA

- **T12**: Validate the new shared-placement Grid adapter with large/scrolling content, complex terminal style constraints and platform input behavior. Divider still needs real-terminal glyph/theme checks and native macOS/Windows coverage. Validate existing Markdown updates and teardown. Coverage/checks: Reactive children/spans, divider orientation, and Markdown content updates pass without new dependencies or custom rendering.

### textual: completed integration QA

- **T13**: Select handles non-editable choices; Input plus a non-focusable OptionList overlay handles editable application-defined candidates. Remaining checks: real terminal IME/paste, screen-reader behavior, narrow/edge placement, large lists, duplicate labels, removal/reordering and rebinding during selection. Coverage/checks: Follow the shared autocomplete acceptance matrix; Pilot input, keyboard/mouse selection, retained editor, external updates and disabled/completion toggles have coverage.

### textual: imperative dialog validation

- **D5 — Imperative dialogs:** Declarative Modal is implemented. Information/Warning/Critical/Confirm/Prompt now use ModalScreen with synchronous
  results from a serial PUI node-event/get_poster callback executor. Native events
  and redraws stay on the UI thread; shutdown releases pending dialog waits.
  No nested event loop is used. Headless pilot tests cover sequential dialogs,
  queued callbacks, prompt values, cancellation and shutdown; real-terminal focus
  and platform checks remain. OpenDirectory/OpenFile/OpenFiles/SaveFile now use
  a shared native ModalScreen picker with separate filesystem I/O workers.
  Pilot tests cover keyboard selection, multi-selection, path edits, filters,
  overwrite/cancellation and shutdown during loading. Real-terminal platform
  checks and large/network-directory performance remain unverified.
