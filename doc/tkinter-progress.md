# tkinter alignment progress

## Baseline and process

PySide6 baseline for all modules: `2b06235fdbbec6e09195ce714c117b03677c6303`.
`95e6cff` supersedes Window/Modal state, Base size policies/redraw guards,
ComboBox invalid selection, and TextField edit caching. `9a3b142` supersedes
ComboBox free-text handling, `675e831` editor/quit lifecycle, and `b9e3ad5`
Tabs placement. Pin newer component SHAs only when adopting later reference behavior.

Work in order: P0 lifecycle, existing controls/layout/scroll, missing components.
Update this document, both references, and Changelog.txt with each change; check
and commit completed changes. Preserve native geometry/ownership and defer
extra dependencies or substantial design choices.

## Current status

Focused editors commit before click callbacks on supported controls. Redraws and
quit run on the native event queue, outside geometry idle flushes, so Scroll
geometry updates cannot reenter reconciliation.

ComboBox now shares selection/free-text resolution: selected items display their
labels while text_model stores values; free typing clears index_model to -1 and
survives redraws, including with both models bound. Unbound selections preserve
keyed identity. This also corrects clear PySide6 edit-buffer loss.


| Priority | Area | Status |
| --- | --- | --- |
| P0 | Application/views | Reuse Tk interpreter, coalesced native event queue, destruction/callback-cancellation guards, queued quit |
| P0 | Reconciliation | Window/Text/Spacer/Canvas retirement links, current mounted-child resolution |
| P1 | Window | Initial-only flags, imperative maximize/fullscreen, obsolete Prop caches removed |
| P1 | Controls | TextField event.value, trace rebinding/suppression, single commits; reactive check/radio clicks |
| P1 | Layout/style | Four-side grid padding, stale weight reset, original native/theme style restoration |
| P1 | Tabs | Native ttk placement, current labels, and owned destruction |
| P1 | Scroll | Outer-container ownership, empty bounds guard, initialized/copied offsets, preserved requests, local wheel filtering |
| P2 | Grid/Divider/dialogs | Native grid spans/padding/resize, ttk.Separator, and standard filedialog/messagebox/simpledialog |
| P2 | Canvas | Native polygon/rectangle/ellipse, text size/color/rotation/anchor parameters, retirement links |
| P2 | ComboBox | Native ttk.Combobox, reactive choices, free text, trace cleanup, and distinct item values |

Scroll resize/end-following behavior needs broader GUI checks. Native tab placement is configured through ttk style.
Canvas text height clipping, cubic paths, image resources, and pointer events
remain incomplete. Remaining visual/data/desktop components still need the design choices below.
Native dialog interaction and broader scrolling/window checks remain pending.

## Validation

`env/` uses Python 3.14.4 with the matching Ubuntu python3.14-tk package installed
locally into its site-packages; system Tcl/Tk libraries are already present.
`env/bin/python -m unittest discover -s tests -p tkinter_regression.py -v`:
12 native display/helper checks passed, including removed callback cancellation
and protection against geometry-triggered reconciliation reentry.
All 17 supported cookbook pages cycle without update errors. The Canvas example
skips cubic drawing on Tkinter; the renderer decision remains open below.
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

## Installation

Backend extras are declared in setup.py: pyside6, wx, flet, textual, and tkinter.
The Tk extra is empty because Tk is native Python/OS support. Generated egg-info
metadata confirms all five extras and their conditional dependencies. See the
README for published-package and local env/ installation commands.
