# Native toolkit reproductions

Small programs that isolate toolkit behavior without importing PUI. These are
manual reproductions, not PUI support guarantees or automated regression tests.

## Flet width constraints

Verified with Flet 1.0.4 and its native Flutter desktop client on macOS,
2026-10-27. Install the desktop runtime and run from the repository root:

```shell
python -m pip install 'flet[desktop]==1.0.4'
python notes/reproductions/flet_tabs_in_layout.py
python notes/reproductions/flet_weight_issue.py
```

The scripts use `ft.run` and the current Tabs/TabBar/TabBarView API. They open
native windows and print actual `on_size_change` measurements. Resize each
window to compare finite allocation with unbounded width. Close the window to
finish. These cases do not require a Web server.

| Case | Expected observation on the recorded runtime |
| --- | --- |
| [Tabs in layout](flet_tabs_in_layout.py) | The expanded inner Column gives Tabs a finite width. The non-expanded inner Column leaves it unbounded and the native callback reports `inf`. Tabs' own expansion is vertical inside the Column; it does not bound horizontal size. |
| [ProgressBar / weight](flet_weight_issue.py) | With both Columns expanded, they share width equally. Expanding only the ProgressBar Column also gives it finite space. An auto-width ProgressBar in a non-expanded Column reports `inf`; an expanded sibling can collapse to zero width. An explicit 300px ProgressBar width stays finite. |

These observations concern constraints in the native Row/Column hierarchy, not
proof that all Flet weight allocation is inconsistent. A ProgressBar height of
4px is normal. The controls with unbounded widths are deliberately retained to
reproduce the problematic layout; the expanded/explicit-width cases provide
controls for comparison. Other platforms and runtime versions need separate checks.

The former ProgressBar experiment inserted the same first Row twice. This version
creates each Row once so duplicate control identity cannot explain the result.
The original scripts used removed Flet APIs and lived in `exp/`.
