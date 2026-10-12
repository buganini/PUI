# flet alignment process and progress

## Contract and baseline

Align backend-neutral declarations, binding, events, reconciliation, and layout
with PySide6. Native Flet APIs remain backend-specific. Reference baseline:
`2b06235fdbbec6e09195ce714c117b03677c6303` for all `PUI/PySide6/*.py` modules.
Window/base/ComboBox/TextField corrections and the user-decided initial-only
window-state contract supersede that baseline at
`95e6cff` (Separate initial window state from imperative state changes).
Add a superseding component SHA only when deliberately adopting later behavior.

Process: P0 lifecycle → existing controls/layout/scroll → missing components.
After each completed change, update this document, both references, and
Changelog.txt, run appropriate checks, then commit. Avoid custom emulation,
extra dependencies, and framework-version migrations without consultation.

## Source audit

- [ ] P0: GUI/session dispatch for FView/PUI and coalesced redraws. Current views
  synchronously call shared sync; determine the supported Flet threading model.
- [ ] P0: consistently call FBase.update to link retired nodes; Button omits it.
- [ ] P1: rebind current TextField handlers, preserve edit buffers, emit event
  values, and avoid duplicate submit/blur commits.
- [ ] P1: Checkbox initial collection membership, reactive labels, current binding,
  and click callbacks; RadioGroup initial selection and current value callbacks.
- [ ] P1: native layout weights/padding/styles and mutation batching. Current code
  frequently suppresses all native update exceptions and updates before mounting.
- [ ] P1: implement scroll requests; current scrollX/scrollY only store fields.
- [ ] P1: initial-only window state plus imperative maximize/fullscreen methods.
- [ ] P2: correct selectable text and Markdown capability reporting.
- [ ] P2/P3: native Grid/Stack/ComboBox/Image/Modal/Splitter/data views/menus,
  canvas shapes/images/pointer events, and desktop integration as supported.

## Decisions to discuss later

- Flet is absent from the available Python runtime. Choose the supported Flet
  version and approve its test-environment installation before changing native
  APIs. Existing source uses ft.app, ElevatedButton(text=...), and the
  Tabs(tabs=...)/Tab(text=..., content=...) API family; do not assume compatibility
  with another version or introduce runtime feature-detection shims.
- Decide the session/UI dispatch policy for timers and background state updates.
- Flet is a single-window backend. Decide which desktop-only PySide6 features
  should remain explicitly unsupported rather than be emulated.
- Shared contract decisions (drag/drop payloads, Canvas anchors, and cancellation)
  are listed in wx-progress.md and apply here too.

## Validation and change log

No Flet runtime checks have run; missing dependencies are not passing tests.
Syntax checks and source corrections will be recorded separately from native
validation. Cookbook capability flags must wait for native checks.

- 2026-10-12: established the source audit, decision list, pinned PySide6 baseline,
  and per-change workflow. Shared TimelineView timer compatibility/retirement fix
  passed one dependency-free regression test and applies to this backend too.
