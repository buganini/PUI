# Web backend plan and remaining work

The experimental Web cookbook runs with `make web` at
`http://localhost:8866/pui/`. This document tracks remaining work only; available
APIs are in [the reference](../REFERENCE.md) and the [wire contract](web-api.md).
The current runtime is Linux-only and serves a cookbook subset. The broader
desktop widget API and browser/platform validation remain incomplete.

## Requested architecture

- Python runs on the server, builds the PUI VDOM from `content()` and State,
  and calculates render diffs against the client's acknowledged state.
- JavaScript applies patches with stable node IDs and base/target revisions.
  Full snapshots establish the initial tree or recover a desynchronized client;
  batch deduplication and ACKs make render retransmission safe.
- Application messages use MessagePack serialization and Zstandard compression.
- State bindings synchronize by the server-side `id(obj)` of their owning
  object, together with the bound attribute/key/index. Identity is scoped to the
  client session; Python remains authoritative for values and callbacks.
- Each client has a dedicated forked Python process. That worker handles one
  client and processes its events serially; the HTTP entry server can serve many
  clients concurrently.
- Canvas painter calls execute in Python, producing drawing commands that the
  browser replays through Canvas 2D.

Transport: HTTP for the page and packaged static assets, with a binary
WebSocket for bidirectional application messages. One browser tab/connection
corresponds to one client. Static asset requests do not create workers.
The entry page, assets and WebSocket must respect configurable `base_url`, with
a separate upstream mount path for proxies that strip the public URL prefix.

```mermaid
flowchart LR
    A[Browser A: patch applier and Canvas 2D]
    B[Browser B: patch applier and Canvas 2D]
    H[HTTP entry server and WebSocket routing]
    F[Clean fork supervisor]
    W1[Worker A: State, callbacks, VDOM diff, painter]
    W2[Worker B: State, callbacks, VDOM diff, painter]
    A <-->|MessagePack + Zstandard| H
    B <-->|MessagePack + Zstandard| H
    H -->|create and reap| F
    F -->|fork for A| W1
    F -->|fork for B| W2
    H <-->|bounded private IPC for A| W1
    H <-->|bounded private IPC for B| W2
```

The gateway uses aiohttp and the standard-library `forkserver` context with an
empty preload list. Its clean supervisor forks workers before PUI/application
imports. The diagram shows the gateway that owns network connections and
relays binary messages to workers. It does not require passing live HTTP/TLS
protocol objects across a fork. Worker application state stays private.

## Baseline and existing integration points

Source audit: `8074c0a8011e63c56063841ce0279a6cf91a981e` (2026-10-15).
Use this commit's shared core and PySide6 behavior as the initial reference;
record a newer component baseline only when intentionally adopting a change.

- [PUIView](../PUI/view.py) rebuilds declarations, tracks State subscriptions,
  and permits independent subview redraws. Its global view registry becomes
  worker-local through process isolation.
- [dom.sync](../PUI/dom.py) already reconciles Python node identity, retires old
  handles, manages virtual children, and invokes backend update/child hooks.
  Preserve these lifecycle rules; the Web hooks should maintain serializable
  render records rather than native widgets. Python diffs these records against
  the acknowledged render state; JavaScript applies the resulting operations.
- [PUINode](../PUI/node.py) keys are not globally unique: repeated unkeyed nodes
  are valid. Its `serialize()` produces diagnostic text, not a wire format.
  Assign separate session-local wire IDs and write an explicit schema.
- [TimelineView](../PUI/timeline.py) uses timer threads. Queue redraw requests
  onto the worker's application loop; never reconcile concurrently with an event.
- [State bindings](../PUI/state.py) recreate AttrBinding/ListBinding/DictBinding
  wrappers on each `state(key)` call. Identify their source with
  `id(binding.state)`, binding kind and key; [table editing](../PUI/_table.py)
  already uses that source identity to detect rebinding.
- Importing [PUI](../PUI/__init__.py) can start a jurigged watcher when installed.
  The forkserver uses an empty preload list, keeping application imports and
  watchers outside the supervisor. The cookbook gateway imports its launcher
  class; workers import and initialize their applications independently.
- [PySide6 Canvas](../PUI/PySide6/canvas.py) supplies the painter signatures;
  [the reference](../REFERENCE.md#canvas) supplies logical-pixel, density, and
  event contracts. Native Qt quirks are findings to review, not wire semantics.

The shared framework retains Python 3.9 support. Select compatible Web
dependencies or discuss a backend-specific minimum; do not raise the shared
minimum. Standard-library `compression.zstd` was added in Python 3.14, so it
cannot be the only implementation for a Python 3.9 Web backend.
See [Python's Zstandard API](https://docs.python.org/3.14/library/compression.zstd.html).

## Lifecycle validation still needed

Further checks are needed for multi-hour connection/expiry/shutdown races and
descriptor/memory soak tests across larger application workloads. The repeatable
finite harness is `tests/web_soak.py`; measured results belong in the reference.
The clean fork supervisor behind `Application.start()` is Linux-only; other
platforms need a separate startup/process design.
Remote/container proxy deployments still need end-to-end checks with explicitly
configured IP/CIDR trust, public ports and their actual network topology.

## API integration still needed

The current intermediate contract and unimplemented capabilities are in [web-api.md](web-api.md). It defines
bootstrap/framing, message envelopes, server-generated patches, snapshot recovery,
object-ID bindings, ordered edits/events, Canvas commands, resource lifetime and
flow control.
Only the advertised capabilities are enabled; the remaining protocol sections
do not imply support for those widgets.

- Run shared malformed-frame/message fixtures on Firefox/Safari and measure
  decoder limits there; add schemas with new Canvas/resource capabilities.
- Extend binding lifetime checks to long-running registration churn.
- Validate native desktop/mobile IMEs, focus retention across browser engines,
  and widget geometry/Stack overlay hit-testing on other engines. Repeat the
  Chrome recovery and TimelineView update scenarios there.
- Stress long-running application callbacks and image decode/cache churn beyond
  the finite DOM, IPC and image regression checks.
- Validate Canvas pointer capture on native touch devices and other browser
  engines. Validate image loading, format support, resampling and memory peaks
  across other browser engines and larger workloads.

## Prioritized implementation backlog

Every row lists **remaining work**; internal helpers do not establish end-to-end
support. Work through P0 first, skipping decision-blocked items while continuing
independent work.

| ID | Priority | Remaining work | Acceptance check / decision dependency |
| --- | --- | --- | --- |
| W1 | P0 | Firefox/Safari framing and message validation | Run the shared malformed fixtures and current dispatch checks on additional browser engines; D3 |
| W2 | P0 | Multi-hour/application lifecycle soak checks | Extend the finite harness to long-running descriptor/memory and expiry/shutdown workloads |
| W4 | P0 | Native IME and cross-engine focus/recovery validation | Real input methods and recovery behavior on browsers beyond Chrome |
| W5 | P0 | Grid track sizing alignment, specification conflicts and cross-engine layout | Resolve D7 before broader sizing changes; repeat Chrome desktop/mobile viewport geometry checks on Firefox/Safari and devices; D3 |
| W8 | P1 | Image portability and resource stress checks | Firefox/Safari formats, resampling, animated images, long-running cache churn, decode memory peaks and rapid file-replacement races |
| W11 | P1 | Table extensions, Tree and declarative dialogs | Table column resizing, sorting, embedded widgets, virtualization/multi-selection and cross-engine/native IME and duck-typed adapter checks remain; Tree is unimplemented. Dialog/result decisions before implementation |
| W12 | P1 | Broader installed-package environment validation | Python 3.9/3.14 Web/dev extra installation and wheel assets are checked; other server platforms and browser versions remain unverified |
| W13 | P2 | HTML/Markdown, Splitter, files and window commands | Explicit browser semantics and new dependency decisions before implementing these features |
| W14 | P2 | Accessibility and application/browser performance validation | Screen readers, CPU/RSS for real workloads, browser/network latency, Canvas throughput and scaling beyond the small fixture |

Initially propose one browser page per Application. Additional native windows,
MDI, native-widget interop and synchronous desktop dialogs need a browser-specific
contract. Fullscreen is subject to browser user-activation rules; maximize cannot
be promised as an OS-window operation. Window icons and fullscreen still need
implementation; their constructor options are accepted with warnings and ignored
so shared desktop declarations can run.

## Decisions before dependent implementation

- **D7 — Layout specification conflicts:** [Layout.html](Layout.html) describes
  five expansion priorities (0–4) under a heading saying four. Its Scroll
  examples use priorities 1/2 while the concepts assign shrinkable widgets 3;
  growable examples also alternate between 1 on both axes and 2 on the
  container's own axis. Web follows the axis-specific container priorities
  (HBox 2/1, VBox 1/2) and Scroll priority 3 on enabled scrolling axes, matching
  the existing wx policy. Higher priorities compete along the parent's main
  axis; cross-axis expansion remains independent, as in wx. Weighted examples
  show priority 4 on both axes, but existing linear-container weights apply
  only along the parent's main axis; Web retains that API behavior.
  The document also calls explicit growable dimensions minimum sizes and
  requires content-fitting growth, whereas Web already allows bounded nested
  containers to shrink and uses explicit Canvas dimensions as fixed sizes.
  Those semantics remain unchanged pending clarification; do not infer a
  shared size/min-size/max-size contract or propagate child priorities through
  container boundaries. Grid track allocation is outside this linear-layout
  change and still needs its own alignment review.
- **D3 — Browser baseline:** Chrome is tested. Validate Firefox/Safari before
  claiming support. The approved build uses @msgpack/msgpack, @bokuweb/zstd-wasm
  and esbuild; additional dependencies still require approval.
- **D6 — Remaining browser mappings:** agree dialogs, files and desktop window
  behavior when reached. Any pixel-exact cross-backend image resampling or
  server-side pixel access would require a separate design.

## Implementation and validation process

Use Application/PUIView classes and explicit arguments for new public APIs.
Start with backend-local render records, public browser DOM/Canvas APIs and
existing shared bindings. Avoid monkey patches, hidden whole-DOM rebuilds and
new frameworks introduced solely to bypass lifecycle work.

For each completed implementation change, run focused checks, update
[REFERENCE.md](../REFERENCE.md), [Reference.html](Reference.html), cookbook
availability and [Changelog.txt](../Changelog.txt) as applicable, then commit.
Remove completed rows from this backlog; keep missing/partial behavior, pending
decisions and unverified checks. Move established contracts into the reference.
Do not add delivery/completion sections or temporary artifact paths.

Validation must include Python/JS protocol fixtures, real browser interaction,
two-worker isolation, lifecycle teardown and Canvas replay. Test immutable render
retries, lost/duplicate ACKs, wrong bases, partial application failure, snapshot
recovery and late/duplicate events. Check local typing ahead of server state,
empty patches confirming rejected edits, changing handlers,
recreated binding wrappers, shared bound slots, object ID reuse, registry cleanup,
list index shifts, dictionary slot recreation, reordered nodes, resize storms,
backpressure, malformed frames and disconnect during painting. Compare server
patch results against target records and Canvas commands deterministically,
and use browser pixels/geometry checks where
visual behavior matters. DOM mocks alone do not establish focus, IME, Canvas or
layout correctness.

Run existing shared lifecycle/State tests and `make check-python39` if shared
code changes. Keep Web runtime/browser checks separate from the existing Qt
baseline. Document the actually tested browsers and server versions; no broader backend support flags or performance guarantees before validation.
