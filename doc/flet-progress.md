# flet alignment progress

## Baseline and process

PySide6 baseline for all modules: `2b06235fdbbec6e09195ce714c117b03677c6303`.
`95e6cff` supersedes Window/Modal state, Base size policies/redraw guards,
ComboBox invalid selection, and TextField edit caching. `6722caa` supersedes
ProgressBar fractional range conversion. Record newer component
SHAs only when adopting later behavior.

Work in order: P0 lifecycle, existing controls/layout/scroll, missing components.
Update this document, both references, and Changelog.txt with each change; check
and commit completed changes. Defer dependencies and substantial native choices.

## Current status

Focused editors commit before click callbacks on supported controls. Flet tracks
native focus without an undocumented blur method and dispatches imperative
window-state changes to its session loop. Qt/wx ignore stale queued quit calls;
Flet quit tears down PUI timers/views before closing the native window.


ComboBox now shares selection/free-text resolution: selected items display their
labels while text_model stores values; free typing clears index_model to -1 and
survives redraws, including with both models bound. Unbound selections preserve
keyed identity. This also corrects clear PySide6 edit-buffer loss.


| Priority | Area | Status |
| --- | --- | --- |
| P0 | Views/lifecycle | FView/PUI coalesce redraws on the session loop; current context preserved; destroyed nodes ignored |
| P0 | Mutation batching | One page update after reconciliation; no child update calls or blanket native exceptions |
| P1 | Window | Page.window API, initial flags, imperative maximize/fullscreen, icon/size/title |
| P1 | Controls | Current Button(content), Text(on_tap), editor/check/radio binding and callback reuse |
| P1 | Layout/style | Native Container shells hold weight, dimensions, four-side padding/margins and backgrounds; text styles reset |
| P1 | Scroll | Native async scroll_to requests and auto_scroll END; client behavior checks pending |
| P2 | Tabs | Current Tabs/TabBar/TabBarView; native page identities/selection preserved across keyed moves |
| P2 | Stack | Native Stack composition with native paint ordering |
| P2 | Canvas | Current Text/Path/Rect/Oval; cubic paths, resize dimensions, rotation; no infinite widget size |
| P2 | Image/ComboBox | Native image bytes/reload and Dropdown with typed item values and editable text |
| P1 | Progress | Fractional value clamp and native zero-range indeterminate state |
| Packaging | Runtime | Optional QPUIQ[flet] extra targets Flet >=1.0.4,<2 |

Tabs supports NORTH/SOUTH; EAST/WEST require a separate native design. Inherited
container fonts, canvas resources/pointer events, and missing components remain pending.

## Runtime and validation

User decision: use latest Flet. Installed flet/flet-desktop/flet-web 1.0.4 in
env/ and migrated directly to the 1.x APIs without compatibility shims.
Reference: [official migration guide](https://flet.dev/docs/updates/migrate-to-1-0/).

`env/bin/python -m unittest discover -s tests -p flet_regression.py -v`:
8 real-Flet Session/patch/control tests passed using a recording message
transport. They cover native constructors, style/binding reuse, keyed Tabs
selection, initial window state, editor commits, redraw batching, Dropdown values, native
canvas shapes, image bytes, progress clamp, and END request configuration. This is
framework/session coverage, not a Flutter visual-client test. Syntax/import
checks pass; Live web-client smoke checks passed for counter updates, editor commits,
Tabs switching, and canvas text/rectangle/cubic rendering. Snapshot:
`/tmp/pui-flet-smoke.jpg`. Full cookbook and scroll interaction checks follow. Worker-thread tests require
normal process socket access: the sandbox blocks asyncio executor shutdown
wakeups; a standalone stdlib reproducer passes outside it. No Python patch or
production workaround was added.

## Decisions to discuss

- Canvas ImageResource crop/scale/source rectangles need a server-side decoder
  (such as Pillow); no extra imaging dependency has been installed.
- Native canvas pointer event composition and text height clipping remain pending.
- Grid row/column spans do not map directly to native GridView; agree the layout
  strategy instead of adding manual pixel-position algorithms.
- Imperative dialogs are async services in Flet 1.x; agree the common return/API
  contract before emulating synchronous dialogs.

- Decide which PySide6 desktop features should remain unsupported in this
  single-window backend.
- Shared drag/drop, Canvas anchor/bounds, and cancellation decisions are recorded
  in wx-progress.md.

## Installation

Backend extras are declared in setup.py: pyside6, wx, flet, textual, and tkinter.
The Tk extra is empty because Tk is native Python/OS support. Generated egg-info
metadata confirms all five extras and their conditional dependencies. See the
README for published-package and local env/ installation commands.
