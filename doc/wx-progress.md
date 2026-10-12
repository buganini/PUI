# wx alignment progress

## Baseline and contract

PySide6 baseline for all modules: `2b06235fdbbec6e09195ce714c117b03677c6303`.
`95e6cff` supersedes Window/Modal state, Base size policies/redraw guards,
ComboBox invalid selection, and TextField edit caching. Pin another component
SHA only when intentionally adopting newer reference behavior.

Align backend-neutral declarations, binding, events, reconciliation, and layout.
Preserve native wx ownership and appearance; Qt-specific options are excluded.
Window maximize/fullscreen constructor flags are initial-only; imperative methods
change live state. Update this document, both references, and Changelog.txt with
each change and commit each completed, checked change.

## Current status

| Priority | Area | Status |
| --- | --- | --- |
| P0 | Reactive views | wx PUI decorator, coalesced GUI redraws, retired/destroyed guards |
| P0 | Ownership | Direct destruction, retired links, keyed reuse, safe native parenting and content replacement |
| P0 | Layout | Current-child expansion/weights, four-sided padding, dimension resets, Grid replacement |
| P1 | Styles | Native font/color/background restoration, including zero colors |
| P1 | Controls | Silent editor updates, single commit, current bindings/callbacks, empty ComboBox, fractional progress |
| P1 | Scroll | Start/end offsets, END, user-position preservation, content growth, native axis policies |
| P1 | Window | Initial-only state with imperative methods, icons, keypress, quit/close accelerators |
| P1 | Dialogs | dir/directory aliases, optional save default, Qt/wx filters; native interaction checks pending |
| P2 | Visual components | Native Tabs/Tab, selectable text, Image dimensions/reload, HTML subset |
| P2 | Canvas | Cubic paths, image resources/drawing, enter/leave, wheel modifiers, removed-paint guard |
| P3 | Menus | Native MenuBar/Menu/MenuAction; reactive labels, keyed moves, rebound callbacks |
| P1 | PySide6 ProgressBar | Fractional maximum converted to native integer hundredths; Qt check pending |
| Shared | TimelineView | Daemon API, retired-node resolution, rescheduling/removal |

Native creation-style changes remount the affected control. Weighted Image
fill/stretch remains pending. Canvas text bounds/anchors require the shared
contract review below. Table/Tree, Toolbar, MDI, interop, Matplotlib, Stack,
Splitter, Modal, and rich Markdown have not been implemented for wx.

## Validation

- wxPython 4.2.4, wxWidgets 3.2.9, Linux GTK display.
- `python3 -m unittest discover -s tests -p wx_regression.py -v`: 15 passed.
- `python3 -m unittest discover -s tests -p timeline_regression.py -v`: 1 passed.
- 17 dependency-free cookbook pages cycled without update errors/native crashes;
  TimelineView was checked separately; DrawShapely needs absent Shapely.
- PySide6 source compiles; its 4 new native regression tests are skipped because
  PySide6 is absent. No Qt runtime comparison is claimed.
- Manual native dialogs, display scaling, and other platforms remain unchecked.

## Decisions to discuss

- Stack: native composition versus a custom overlay sizer.
- Splitter: limit to native wx's two panes or compose additional splitters.
- Modal: nested ShowModal loop versus platform-specific window-modal behavior.
- Table: wx.grid editors/renderers versus DataView for separate edit/display
  values, typed choices, and duplicate labels.
- Tree: TreeCtrl reconciliation versus DataView stable identity; TreeCtrl cannot
  move items natively. Avoid rebuilding away selection/expansion.
- Toolbar: one native wx.Frame toolbar versus PySide6's multiple toolbars.
- MDI: target platforms and native host strategy.
- Interop: borrowed-widget ownership and restoring the original parent on removal.
- Dependencies: approve PySide6 comparisons, optional Matplotlib/Shapely, and
  rich Markdown rendering before installing anything.
- Shared contracts: backend-neutral drag/drop payloads; Canvas text anchors/bounds;
  OpenDirectory cancellation (Qt empty string versus wx None).
