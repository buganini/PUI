# Cross-backend backlog

This list collects framework-wide work and API ideas. Backend-specific gaps and
validation tasks belong in the [progress documents](README.md#remaining-work).
Ideas below are not committed API plans.

## Diagnostics

- Include layout parameters in declaration-tree dumps and add regression coverage
  for the output. The existing [dump example](../PUI/examples/dump.py) demonstrates
  tree structure.

## API ideas

- Lazy / virtualized lists: define item creation, keyed retention and disposal
  behavior before adding a common API.
- Navigation stack and view router: define history, state retention and lifecycle
  semantics.
- Canvas arc drawing: define a common helper and its angle/direction conventions.
- State integration with Pydantic: explore validation and binding behavior.

## Existing capabilities and related follow-up

- Nested reactive data is available through `State(data, deep=True)`; initialize
  view-local state in `setup()`. See the [State implementation](../PUI/state.py).
- Tab placement is exposed through `Tabs(tabposition=...)`; platform/backend
  limits are documented in the [Tabs reference](../PUI/doc/Reference.html#tabs).
- Modal windows and overlapping children already have public APIs:
  [Modal](../PUI/doc/Reference.html#modal) and
  [Stack](../PUI/doc/Reference.html#stack). A separate SwiftUI-style overlay
  modifier would need requirements beyond the current Stack behavior.
- Flet layout/Scroll validation is tracked in [Flet progress](flet-progress.md)
  and the [native toolkit reproductions](reproductions/README.md), rather than
  retaining the old unqualified cookbook sizing issue here.
