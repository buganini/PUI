# tkinter alignment process and progress

## Contract and baseline

Align backend-neutral declarations, binding, events, reconciliation, and layout
with PySide6, preserving native Tk ownership and geometry managers. Reference
baseline: `2b06235fdbbec6e09195ce714c117b03677c6303` for all PySide6 modules.
Window/base/ComboBox/TextField fixes and the user-decided initial window state
contract supersede it at `95e6cff`. Pin a newer component SHA only when adopting
later reference behavior.

Process: P0 lifecycle → existing controls/layout/scroll → missing components.
Update this document, both references, and Changelog.txt after each completed
change; run checks and commit it. Record decisions and move on when dependencies
or substantial native design choices need consultation.

## Source audit

- [x] P0: coalesce redraws and route virtual subviews through native Tk's queue;
  currently subviews with no ui call sync directly, including timer callbacks.
- [x] P0: direct destruction/retired-node ownership and safe parent lookup.
- [x] P0: call shared update from Window, Text, and Spacer; resolve mounted
  child references after reuse. Canvas is addressed in the next change.
- [x] P1: fix TextField callbacks currently calling _input/_change without their
  required event argument, suppress programmatic traces, and rebind traces safely.
- [x] P1: reactive Checkbox/RadioButton labels/values and click callbacks.
- [x] P1: remove Tabs destruction copied from Qt (widgets/deleteLater attributes).
- [x] P1: native grid padding/weight resets and style restoration.
- [ ] P1: Scroll empty bounds, outer-container lifecycle, local wheel bindings,
  position preservation, and requested start/end offsets.
- [x] P1: initial-only window state and imperative maximize/fullscreen methods.
- [ ] P2: native ComboBox, Grid, Divider, dialogs, and canvas shape APIs.
- [ ] P2/P3: remaining visual/data/desktop components as native support allows.

## Decisions to discuss later

- tkinter and _tkinter are absent from the available Python runtime. Approve a
  Tk-enabled test runtime before claiming native GUI validation.
- Decide last-window close behavior with Tk's hidden application root; avoid
  guessing whether closing one Toplevel should quit all other windows.
- Text-widget width/height units are characters/lines, while PySide6 uses logical
  pixels. Agree whether wrapper containers should enforce pixel dimensions.
- Rich HTML/Markdown and general image format/scaling support need dependencies
  or explicitly limited native coverage; do not add custom parsers/resamplers.
- Cubic Bezier drawing needs an approximation strategy or another renderer:
  Tk's smooth line options do not directly implement the same cubic path API.
- Data-view editing, drag/drop payloads, and desktop-only feature coverage need
  the same shared contract review as wx.

## Validation and change log

No Tk runtime checks have run; absence of tkinter is not a passing test result.
Record syntax checks separately and leave native/manual acceptance items open.

- 2026-10-12: established the source audit, decision list, pinned PySide6 baseline,
  and per-change workflow. Shared TimelineView timer compatibility/retirement fix
  passed one dependency-free regression test and applies to this backend too.

- 2026-10-12: source-only P0/control pass: Application reuses its Tk interpreter
  instead of creating one per redraw; virtual views coalesce native after_idle
  requests, and native destruction respects direct ownership. Window/Text/Spacer
  link retired nodes; layouts resolve current children, preserve four-side grid
  padding, and clear obsolete weight groups. Styling restores native options and
  uses ttk style APIs for ProgressBar. TextField emits required event.value,
  removes/rebinds traces and focus handlers, silently updates models, preserves
  edits, and commits once. Checkbox/RadioButton update labels/values and click
  callbacks. Removed Qt-only Tabs destruction. Window flags are initial-only
  with imperative methods, no Prop caches; Application exposes queued quit.
  Validation: compileall passed; 3 native unittest scenarios skipped because
  tkinter is absent. Checked boxes mean source changes delivered, not native
  acceptance. Pixel dimension units and last-window close behavior remain open.
