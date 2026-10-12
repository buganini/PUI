# tkinter alignment progress

## Baseline and process

PySide6 baseline for all modules: `2b06235fdbbec6e09195ce714c117b03677c6303`.
`95e6cff` supersedes Window/Modal state, Base size policies/redraw guards,
ComboBox invalid selection, and TextField edit caching. Pin newer component SHAs
only when adopting later reference behavior.

Work in order: P0 lifecycle, existing controls/layout/scroll, missing components.
Update this document, both references, and Changelog.txt with each change; check
and commit completed changes. Preserve native geometry/ownership and defer
extra dependencies or substantial design choices.

## Current status

| Priority | Area | Status |
| --- | --- | --- |
| P0 | Application/views | Reuse Tk interpreter, coalesced native subview queue, destruction/idle-cancellation guards, queued quit |
| P0 | Reconciliation | Window/Text/Spacer/Canvas retirement links, current mounted-child resolution |
| P1 | Window | Initial-only flags, imperative maximize/fullscreen, obsolete Prop caches removed |
| P1 | Controls | TextField event.value, trace rebinding/suppression, single commits; reactive check/radio clicks |
| P1 | Layout/style | Four-side grid padding, stale weight reset, original native/theme style restoration |
| P1 | Tabs | Removed Qt-only destruction code |
| P1 | Scroll | Outer-container ownership, empty bounds guard, initialized/copied offsets, preserved requests, local wheel filtering |
| P2 | Canvas | Native polygon/rectangle/ellipse, text size/color/rotation/anchor parameters, retirement links |
| API | ComboBox names | Canonical and legacy unsupported aliases exported |

Scroll resize/end-following behavior and native tab placement need GUI checks.
Canvas text height clipping, cubic paths, image resources, and pointer events
remain incomplete. Grid/Divider/ComboBox/dialogs and remaining visual/data/desktop
components are still pending implementation after native validation is available.

## Validation

`env/` uses Python 3.14.4 with the matching Ubuntu python3.14-tk package installed
locally into its site-packages; system Tcl/Tk libraries are already present.
`env/bin/python -m unittest discover -s tests -p tkinter_regression.py -v`:
6 native GTK-display checks passed, including removed idle callback cancellation.
Window-state checks wait for the window manager acknowledgement.
Core corrections: `7b76a99`; Scroll/Canvas: `b1a3188`. Syntax checks pass.

## Decisions to discuss

- Agree pixel dimensions versus Tk text character/line units and wrapper sizing.
- Agree last-window close behavior with the hidden Tk application root.
- Rich HTML/Markdown and general image format/scaling need dependencies or a
  deliberately limited native contract; do not add custom parsers/resamplers.
- Cubic paths need an agreed approximation or another renderer; smooth Tk lines
  are not the same cubic API.
- Data-view editing, drag/drop, Canvas bounds/anchors, and desktop feature coverage
  need the shared native contract review.
