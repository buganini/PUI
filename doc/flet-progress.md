# flet alignment progress

## Baseline and process

PySide6 baseline for all modules: `2b06235fdbbec6e09195ce714c117b03677c6303`.
`95e6cff` supersedes Window/Modal state, Base size policies/redraw guards,
ComboBox invalid selection, and TextField edit caching. Record newer component
SHAs only when adopting later behavior.

Work in order: P0 lifecycle, existing controls/layout/scroll, missing components.
Update this document, both references, and Changelog.txt with each change; check
and commit completed changes. Defer dependencies and substantial native choices.

## Current status

| Priority | Area | Status |
| --- | --- | --- |
| P0 | Node lifecycle | Button retirement link, Application/FView destruction guards corrected in source |
| P0 | GUI dispatch | Pending supported Flet version/session policy |
| P1 | TextField | Current handlers, edit-buffer preservation, normalized single submit/blur commit |
| P1 | Checkbox/RadioButton | Membership/initial selection, labels, current binding, click callbacks |
| P1 | Spacer | Default expansion applied |
| P2 | Text | Native selectable flag and existing Markdown capability reporting |
| API | ComboBox names | Canonical and legacy unsupported aliases exported |

Layout/style/padding parity, native mutation batching, window-state methods,
scrolling (currently only stores requests), canvas APIs, and missing components
remain pending the supported native API version. Cookbook flags have not been
expanded based on unvalidated source changes.

## Validation

`python3 -m compileall -q PUI/flet` passed. Flet is absent from the Python runtime;
no GUI/session tests ran and no fake runtime was substituted. Source fixes are
committed as `dfcefc8`; native acceptance remains open. Shared TimelineView has
one passing dependency-free regression test.

## Decisions to discuss

- Choose the supported Flet version and approve a test-runtime installation.
  Existing source uses ft.app, ElevatedButton(text=...), and
  Tabs(tabs=...)/Tab(text=..., content=...). Do not add version-detection shims.
- Agree session/UI dispatch for timers and background state updates.
- Decide which PySide6 desktop features should remain unsupported in this
  single-window backend.
- Shared drag/drop, Canvas anchor/bounds, and cancellation decisions are recorded
  in wx-progress.md.
