# wx alignment progress

Autocomplete validation must follow the [shared acceptance criteria](https://buganini.github.io/PUI/doc/Reference.html#autocomplete-acceptance); unverified cases remain pending, including real IME and platform-specific focus behavior.

Only unfinished work is listed below. **Missing** means the named behavior has
no implementation; **Partial** means an implementation exists but the listed gap
remains; **Unverified** means code exists but the stated runtime check is pending.
Completed changes belong in the changelog and reference, not the backlog.

## Missing or incomplete behavior

| Priority | Area | State | Remaining work |
| --- | --- | --- | --- |
| P1 | Image sizing | Partial | Scale/fill weighted images when their allocated size changes, beyond explicit dimensions |
| P1 | Canvas text | Partial | Resolve shared text anchors/bounds, implement width/height clipping, and verify font-dependent measurements |
| P2 | Stack | Unverified | Windows Cookbook text layer order visually checked at normal/maximized sizes with wxPython 4.3.2 / wxWidgets 3.3.4 after declaration-order text composition fix; pixel tests cover text layer order, reorder, hide/show and resize. Verify keyboard focus, pointer hit testing, mixed native controls and macOS transparency. Linux geometry, resize, keyed reorder and removal and Windows retained text updates/reorder have regression coverage |
| P2 | Modal | Missing | Agree native modal lifecycle and result/cancellation handling |
| P2 | Table | Partial | Additional editor types and large-data optimization beyond the current per-cell attributes/content autosizing need scope decisions |
| P1 | Table portability | Unverified | Recheck decorated editor focus, keyboard commit/cancel and choice handling on Linux/Windows. The editor now uses wx.Control (or the native field directly), not wx.Panel; macOS wxPython 4.3.2 passes tests/wx_table.py. This does not verify every 4.3 release/platform. |
| P3 | Toolbar | Missing | Agree one native toolbar versus PySide6's multiple-toolbar model |
| P3 | MDI/interop | Missing | Agree platform scope, native hosts, and borrowed-widget ownership |
| P3 | Matplotlib/Markdown | Missing | Approve dependencies and native integration; Markdown currently falls back to plain text |
| Shared | Drag/drop | Partial | Native Window targets support files/text/URLs; sizer-only targets, outgoing drags and real OS cross-platform drag validation remain |
| Shared | Dialog cancellation | Partial | Resolve OpenDirectory's wx None versus PySide6 empty-string result |

## Validation still needed

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
| Canvas rendering | Unverified | Broaden per-paint style reuse, redundant-setter skipping, nested pen/brush push/pop, text/geometry/image ordering, HiDPI and HeavyCanvas throughput checks to macOS/Windows; measure native 120,000–1,000,000-session presets and memory use; Linux GTK mixed primitives and nested Shapely holes are covered by tests/wx_canvas.py |
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
[shared/Qt Python 3.9 check](pyside6-reference.md#python-39-compatibility) does not cover wx.

### Visibility and adaptive layout

- **Unverified:** macOS/Windows focus handling when `.visible(False)` hides the focused control; Linux retained-control toggling is covered by regression tests.

Adaptive Layout: content-size observations, retained State and threshold transitions have Linux regression coverage; macOS/Windows theme, DPI and nested scrolling geometry checks remain.

### Divider validation

Divider thickness, expansion and retained orientation changes need native macOS/Windows
validation. Linux GTK checks cover HBox/VBox resizing, virtual views and direct
HVBox/VHBox direction changes in [divider_native.py](../tests/divider_native.py).

## Decisions to discuss

- Modal, Toolbar, and MDI: resolve the native choices
  listed in their backlog rows before adopting custom composition.
- Interop: agree borrowed-widget ownership and restoring original parents.
- Dependencies: approve Matplotlib, Shapely, and rich Markdown dependencies before
  installation or adding extras.
- Shared contracts: Canvas text anchors/bounds, and
  OpenDirectory cancellation.

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
rows, retain pending checks, and avoid temporary artifact paths.
See [README](../README.md) for installation and [common reference](https://buganini.github.io/PUI/doc/Reference.html)
for implemented behavior.
