# Pyodide remaining work

Autocomplete validation must follow the [shared acceptance criteria](https://buganini.github.io/PUI/doc/Reference.html#autocomplete-acceptance); unverified cases remain pending, including real IME and platform-specific focus behavior.

The static cookbook and browser-local backend are implemented. Usage, architecture,
fixed CDN runtime and publishing instructions are in
[Pyodide reference](pyodide-reference.md). This document lists only missing work,
partial coverage and unresolved decisions; remove items when resolved.

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

## Missing implementation and coverage

| ID | Priority | Remaining work | Acceptance check |
| --- | --- | --- | --- |
| Y2 | P0 | Blocking `PUIView.wait()` has no browser-safe equivalent. Application code must currently avoid it. | Define a compatible awaitable/event-loop API before advertising blocking-wait parity. Never block the worker loop or patch threading. |
| Y5 | P1 | Native control and selection suites pass; the full Web geometry, IME and stale-binding matrices have not all been rerun through Pyodide. | Run native browser interaction/resize cases, including mixed fixed/flexible sizing and composition. |
| Y6 | P1 | Tabs/Views/Table use shared implementations; malformed/stale list/dict binding and editor-lifetime coverage still needs the actual Pyodide bridge. | Repeat binding invalidation and delayed-input cases in the worker, beyond shared Python regression coverage. |
| Y7 | P1 | HeavyCanvas hover, zoom and command deltas are exercised; cross-engine Canvas style reuse/invalid-command handling, long-running continuous painters, synthetic backpressure and prolonged background-tab behavior remain unverified. | Bounded queues/resources and matching revisions after repeated foreground/background changes and resize. |
| Y8 | P1 | Bundled Image works; local Canvas image crop/scale, failed decode and sustained image-revision churn need browser coverage. | No stale Blob URL access or leak while decode, remove, replace and restart overlap. |
| Y10 | P1 | Firefox, Safari/mobile browsers and memory/proxy soak tests are unverified. | Check module-worker loading, native controls, long callbacks, background lifecycle and repeated teardown on those browsers. |
| Y11 | P2 | General app packaging, persistence, file import/export, offline distribution and graceful interrupt remain unspecified. | Agree each API/deployment policy first; retain the simple transient cookbook bootstrap. |
| Y12 | P2 | DrawShapely/Matplotlib and remaining widgets are not enabled. | Verify browser-compatible packages and actual adapters before adding dependencies/support flags. Loading a wheel alone does not implement its widget. |

Tree, general dialogs, Markdown and MatplotlibCanvas remain unimplemented in
the shared renderer. Direct native-widget hierarchy embedding is outside the
DOM backend contract, rather than a pending renderer adapter. Desktop window
management and user-activation restrictions remain browser limitations.

## Validation scope

On 2026-10-27, `tests/pyodide_bootstrap.cjs` passed against the locally built
static cookbook in macOS Chrome with the actual CDN-loaded Python worker:
CDN failure reporting, archive mismatch recovery, retry, fresh reload and
independent tabs. The test explicitly selects its page instead of relying on
the cookbook's default page, and distinguishes navigation from demo buttons.
`pyodide_runtime` also passed 9 CPython tests; those do not execute WebAssembly.

The public [GitHub Pages cookbook](https://buganini.github.io/PUI/cookbook/cookbook.html)
was also checked on 2026-10-27 in macOS Chrome: the Python worker loaded and
clicking B on the Button page updated State and the displayed label. The public
Reference.html and Layout.html URLs both returned HTTP 200. Deployment is not
an outstanding task.

The full interaction/IME matrix, Firefox/Safari and long-running memory behavior
still require the specific checks listed in Y5–Y10.

## Performance measurements still needed

Use HeavyCanvas's 1,000–30,000-session presets, including hover and broad zoom
changes. Measure cold and warm CDN loads separately; a single startup time is not
a cold-download benchmark. Record browser/device, viewport, DPR and sample count.

Separate painter execution, snapshot collection, structural indexing/diff, Python-to-JS
conversion/null normalization, structured cloning, DOM apply and Canvas replay.
Measure command-tuple construction and the 128-entry integer-color LRU in
the actual Pyodide worker; native CPython timings do not establish the WebAssembly
performance improvement.
Use correlation IDs and context-local timing, reporting median and tail latency.
Track live resources and retained memory during repeated updates. Compare local
structured cloning with MessagePack/transferable buffers before proposing a binary
bridge; neither approach is automatically zero-copy.

## Decisions still open

- General application manifest/build interface and optional self-hosted runtime.
  The cookbook uses the approved fixed official CDN version.
- Explicit persistence/save/load behavior, user file import/export and allowed
  external resource sources. Current State and MEMFS are transient per worker.
- Graceful interruption and cross-origin-isolation deployment, if required.
  Current recovery is worker termination/restart without SharedArrayBuffer.
- Any alternative local binary transport should follow measurements, not assumed
  compression benefits. Current complete batches use plain `postMessage` records.

### Drop validation still needed

Inbound file/text/URL drops have automated browser coverage. Real OS file-manager drags across Safari/Firefox and mobile file sources remain unverified. Directory drops, outgoing drag sources and table row reordering are not supported.

Adaptive Layout: the shared browser ResizeObserver and Python local-bridge size messages are tested separately; verify the combined path in the CDN-backed runtime and across browser engines.

Splitter: shared-renderer mouse/keyboard, nesting and pane-retention checks pass
in Web Chromium. Repeat them through the actual Pyodide bridge and other engines.
