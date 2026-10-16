# wx alignment progress

Only unfinished work is listed below. **Missing** means the named behavior has
no implementation; **Partial** means an implementation exists but the listed gap
remains; **Unverified** means code exists but the stated runtime check is pending.
Completed changes belong in the changelog and reference, not the backlog.

## Missing or incomplete behavior

| Priority | Area | State | Remaining work |
| --- | --- | --- | --- |
| P1 | Image sizing | Partial | Scale/fill weighted images when their allocated size changes, beyond explicit dimensions |
| P1 | Canvas text | Partial | Resolve shared text anchors/bounds, implement width/height clipping, and verify font-dependent measurements |
| P2 | Stack | Missing | Choose native overlay composition and implement child ordering/reconciliation |
| P2 | Modal | Missing | Agree native modal lifecycle and result/cancellation handling |
| P2 | Table | Partial | Additional editor types and large-data optimization beyond the current per-cell attributes/content autosizing need scope decisions |
| P3 | Toolbar | Missing | Agree one native toolbar versus PySide6's multiple-toolbar model |
| P3 | MDI/interop | Missing | Agree platform scope, native hosts, and borrowed-widget ownership |
| P3 | Matplotlib/Markdown | Missing | Approve dependencies and native integration; Markdown currently falls back to plain text |
| Shared | Drag/drop | Missing | Define backend-neutral payloads and lifecycle before implementation |
| Shared | Dialog cancellation | Partial | Resolve OpenDirectory's wx None versus PySide6 empty-string result |

## Validation still needed

| Area | State | Pending check |
| --- | --- | --- |
| TextField placeholder | Unverified | Focus-dependent hint appearance on other platforms; native tests cover hint updates/removal, cursor/edit retention, and binding events |
| Disabled controls | Unverified | Native mouse/keyboard focus behavior across platforms; tests/wx_regression.py covers enabled toggles, retained Button/ComboBox controls, and preserved values/editability |
| Views | Unverified | Manual focus/keyboard transitions and other platforms; selection, retained edits, keyed moves/removal and model replacement are covered by tests/wx_views.py |
| Tabs | Unverified | Broader keyboard/focus and platform behavior; optional models, native selection events, duplicate keys, keyed moves, labels and empty transitions are covered by tests/wx_tabs.py |
| Splitter | Unverified | Manual sash dragging/double-click behavior, minimum sizes at display scaling, and other platforms; native ownership, geometry, resize, redraw, keyed moves and subview updates are covered by tests/wx_splitter.py |
| Tree | Unverified | Manual mouse/keyboard interaction, column sizing on other platforms, and broader platform behavior; native model, hit-testing, selection/expansion and reconciliation tests are in tests/wx_tree.py |
| Table | Unverified | Manual keyboard/mouse editing, selection and scrolling on other platforms; native Grid/editor regression tests are in tests/wx_table.py |
| Dialogs | Unverified | Operate native file/directory, message, and input dialogs; verify cancellation/results |
| Canvas input | Unverified | Exercise native press/release, drag, hover, double-click, wheel coordinates/modifiers, and removal during input |
| Canvas geometry | Unverified | Exercise drawShapely with an approved Shapely runtime |
| Tabs/layout | Unverified | Check HBox/VBox cross-axis centering and native minimum-size behavior on other platforms and display scales; Linux GTK resize/redraw and retained editor expansion are covered. Compare notebook placement with PySide6 |
| Display/platforms | Unverified | Check display scaling, other platforms, and broader cookbook interactions beyond the Table/Views switching regression in tests/wx_views.py |

Existing regression suites: [wx_regression.py](../tests/wx_regression.py) and
[timeline_regression.py](../tests/timeline_regression.py), plus
[wx_table.py](../tests/wx_table.py), [wx_tree.py](../tests/wx_tree.py), and
[wx_splitter.py](../tests/wx_splitter.py), and [wx_views.py](../tests/wx_views.py). The recorded runtime
is wxPython 4.2.4 / wxWidgets 3.2.9 on Linux GTK. Run
`python3 -m unittest discover -s tests -p 'wx_*.py' -v` and
`python3 -m unittest discover -s tests -p timeline_regression.py -v`.
Passing those checks does not complete the pending native checks above.
Legacy decorator warnings, metadata, and argument forwarding are checked in
[decorator_signatures.py](../tests/decorator_signatures.py). Native wx validation
on Python 3.9 remains pending; the separate
[shared/Qt Python 3.9 check](../README.md#python-39-compatibility) does not cover wx.

## Decisions to discuss

- Stack, Modal, Toolbar, and MDI: resolve the native choices
  listed in their backlog rows before adopting custom composition.
- Interop: agree borrowed-widget ownership and restoring original parents.
- Dependencies: approve Matplotlib, Shapely, and rich Markdown dependencies before
  installation or adding extras.
- Shared contracts: drag/drop payloads, Canvas text anchors/bounds, and
  OpenDirectory cancellation.

## Baseline and process

Use backend `Application`/`PUIView` classes for new code and examples. Keep
deprecated decorators covered by compatibility checks during migration.

User decisions: use wx.grid.Grid for Table, wx.dataview.DataViewCtrl for Tree,
and nested wx.SplitterWindow controls for Splitter, nesting in the right/bottom
pane. These are included in wxPython; no new dependency is required.

PySide6 baseline for all modules: `2b06235fdbbec6e09195ce714c117b03677c6303`.
`95e6cff` supersedes Window/Modal state, Base size policies/redraw guards,
ComboBox invalid selection, and TextField edit caching. `6722caa` supersedes
ProgressBar fractional range conversion. `9a3b142` supersedes ComboBox free-text
handling, `675e831` editor/quit lifecycle, and `b9e3ad5` Tabs placement. Pin another
component SHA only when intentionally adopting newer reference behavior.

Align backend-neutral declarations, binding, events, reconciliation, and layout.
Preserve native wx ownership and appearance; Qt-specific options are excluded.
Work through priorities; skip decisions requiring user input and continue
independent items. Update this document, relevant references, and Changelog.txt
after each change; validate and commit each completed change. Remove finished
rows, retain pending checks, and avoid temporary artifact paths.
See [README](../README.md) for installation and [common reference](Reference.html)
for implemented behavior.
