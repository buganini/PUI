# Pyodide remaining work

Latest runtime audit: [2026-10-28 macOS validation](validation-2026-10-28.md).

Autocomplete follows the [shared acceptance criteria](https://buganini.github.io/PUI/doc/Reference.html#autocomplete-acceptance).

The static cookbook and browser-local backend are implemented. Usage, architecture,
fixed CDN runtime and publishing instructions are in
[Pyodide reference](../PUI/doc/pyodide-reference.md). This document lists only missing work,
functional gaps and unresolved decisions; follow-up QA is recorded separately.

Implemented integrations are **complete**. This backlog tracks missing functionality,
known bugs and design decisions. Additional test coverage does not keep a feature
open. Detailed test environments, results and follow-up QA are in
[validation notes](validation-2026-10-30.md#pyodide). Platform names below identify
known differences or specific bugs, not a mandatory three-OS completion matrix.

## Baseline and process

Original API audit: `0f336292379abecaca2e7480e055ebcf17dd560c` (2026-10-16).
Shared browser extraction: `a7eb723` (Python widgets/runtime plus JavaScript
renderer/controller). Use the shared core/PySide6 declarations as the API baseline
and the shared browser renderer for DOM behavior.

Work through P0, P1, then P2. Update this backlog, relevant references, cookbook
support flags and Changelog.txt after each completed change; run relevant checks
and commit. Preserve Python 3.9 compatibility in shared code and host tools.
Consult before new dependencies or policy decisions; continue independent work
while a decision is pending. Do not infer browser support from host-Python tests.

## Missing implementation

| ID | Priority | Remaining work | Acceptance check |
| --- | --- | --- | --- |
| Y2 | P0 | Blocking `PUIView.wait()` has no browser-safe equivalent. Application code must currently avoid it. | Define a compatible awaitable/event-loop API before advertising blocking-wait parity. Never block the worker loop or patch threading. |
| Y11 | P2 | General app packaging, persistence, offline distribution and graceful interrupt remain unspecified. | Agree each API/deployment policy first; retain the simple transient cookbook bootstrap. |
| Y12 | P2 | DrawShapely and remaining widgets are not enabled. | Verify browser-compatible packages and actual adapters before adding dependencies/support flags. Loading a wheel alone does not implement its widget. |

Markdown remains unimplemented in the shared renderer. Tree/TreeNode and adapter support now share the DOM renderer with Web; actual Chrome/Pyodide worker tests cover both cookbook pages, repeated cross-clicks, keyboard navigation and adding nodes. Direct native-widget hierarchy embedding is outside the
DOM backend contract, rather than a pending renderer adapter. Desktop window
management and user-activation restrictions remain browser limitations.

## Decisions still open

- General application manifest/build interface and optional self-hosted runtime.
  The cookbook uses the approved fixed official CDN version.
- Explicit persistence/save/load behavior, user file import/export and allowed
  external resource sources. Current State and MEMFS are transient per worker.
- Graceful interruption and cross-origin-isolation deployment, if required.
  Current recovery is worker termination/restart without SharedArrayBuffer.
- Any alternative local binary transport should follow measurements, not assumed
  compression benefits. Current complete batches use plain `postMessage` records.

## Canvas / Matplotlib functional gaps

The shared adapter renders paths, glyph outlines, mathtext and RGBA images.
See [Canvas Functions](https://buganini.github.io/PUI/doc/Reference.html#canvas-functions) for the capability
matrix and native/no-op clipping behavior. Functional gaps: navigation UI/default shortcuts, hatch, Gouraud shading, cap/join/dash parity, large-image batching and
sustained redraw optimization.

Matplotlib mouse/key callbacks now use the shared input adapter. Web/Pyodide
handle focus, blur, pointer capture and connection resets; native browser input
and Python callback tests cover this path. Pan/zoom algorithms
work with Matplotlib NavigationToolbar2 in tests, but no PUI navigation UI or
wheel-zoom policy is installed automatically.
