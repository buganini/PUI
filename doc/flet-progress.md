# flet alignment progress

Autocomplete validation must follow the [shared acceptance criteria](https://buganini.github.io/PUI/doc/Reference.html#autocomplete-acceptance); unverified cases remain pending, including real IME and platform-specific focus behavior.

This document tracks remaining work against PySide6. Implemented behavior belongs
in [common reference](https://buganini.github.io/PUI/doc/Reference.html), source, and tests. Remove completed items;
keep outstanding validation and decisions. Do not add temporary artifact paths.
**Missing** means the named behavior has no implementation; **Partial** means
implementation exists but the listed gap remains. Validation items below are
**Unverified**, not missing implementations.

## Missing or incomplete behavior

| Priority | Area | State | Remaining work |
| --- | --- | --- | --- |
| P1 | HBox / VBox / HVBox / VHBox reversal | Unverified | inverse/inverseH/inverseV order and Row/Column switching are tested with the recording transport; verify geometry and cursor/scroll behavior in a native Flutter client. Client-only state resets on Row/Column replacement are an accepted limitation documented in the reference |
| P1 | Views | Deferred | Flet 1.0.4 lacks an exposed IndexedStack/Offstage equivalent. Native visibility removes Flutter widgets; TabBarView permits swiping unless its children are also disabled. Await native support for programmatic-only switching with retained page state; the user chose to defer this adapter |
| P1 | Canvas raw input parity | Partial | Middle-button dragging, extra/simultaneous buttons, wheel modifiers and angular deltas are unavailable in the current native gesture API; native timing/cancellation differs from Qt |
| P1 | Window keyboard | Missing | Wire `.keypress` and map keys/modifiers to the common event contract |
| P1 | VBox alignment | Unverified | Native Column START and Row CENTER match the alignment defaults; verify client geometry and expansion |
| P1 | Styles | Partial | Propagate inherited container fonts to descendants |
| P2 | Canvas images | Missing | Implement `ImageResource.load/crop/scale`, `loadImage`, and `drawImage`, including source rectangles and opacity; dependency decision pending |
| P2 | Canvas text/HiDPI | Partial | Implement text height clipping, resolve shared anchor/bounds behavior, and report actual display density instead of the fixed 1.0 fallback |
| P2 | Canvas geometry | Missing | Implement `drawShapely`; optional dependency decision pending |
| P2 | Tabs | Partial | Add Side.Right/Side.Left placement after choosing a native layout approach |
| P2 | Grid | Missing | Implement Grid row/column spans; native layout approach pending |
| P2 | Splitter | Partial | Public Row/Column, size events and GestureDetector provide pointer resizing; a real Linux desktop drag is checked. Keyboard resizing is not implemented. Touch, native macOS/Windows and long-running nested/scrolling panes remain unverified. Row/Column orientation changes can reset Flutter cursor/scroll state despite retained Python controls |
| P2 | Dialogs/Modal | Missing | Implement file/directory dialogs, messages, Confirm/Prompt, and Modal; common async/result contract pending |
| P2 | Table | Partial | Resolve `autofit=False`, additional editor types, stable adapter row identities, and large-data paging; current headers scroll with data and Qt selection parity is absent |
| P2 | Adaptive Grid | Missing | Grid is not implemented. Supporting content-height rows plus row/column spans requires a native composition or a measured layout controller; choose that design before adding a Row/Column approximation. The shared columns/dense algorithm alone does not provide a Flutter Grid renderer. |
| P2 | Tree | Missing | Implement Tree/TreeNode and adapter reconciliation with selection/expansion preservation |
| P3 | Menus/toolbars | Missing | Implement MenuBar/Menu/MenuAction and ToolBar/ToolBarAction |
| P3 | Desktop integration | Missing | Decide scope for MdiArea/MdiSubWindow, multiple windows, and native-widget interop |
| P3 | Rich content | Missing | Implement HTML rendering and MatplotlibCanvas; dependency decisions pending |
| Shared | Drag/drop | Missing | Implement the established inbound files/text/URLs contract using suitable native integration; outgoing drags remain a separate design |

## Validation still needed

- TextField placeholder: live-client empty/focused hint appearance; Session
  tests cover hint updates/removal, native overrides, retained edits, and bindings.
- Disabled controls: live-client pointer/keyboard and focus behavior for Button,
  ComboBox, Checkbox and RadioButton; Session tests cover disabled properties, retained controls and
  values, and adding/removing native disabled overrides.
- Tabs: desktop-client keyboard/swipe behavior, broader rapid-change cases and
  focus retention. Browser clicks and both cookbook selection paths were checked;
  tests/flet_tabs.py covers serialized models, click/change events, duplicate keys,
  labels, keyed moves, rebinding and empty transitions.
- Canvas input: desktop-client/platform coverage, touch cancellation, right-button
  dragging.
- Canvas performance: broaden retained-frame Paint sharing checks to desktop
  clients/platforms and measure shape construction, Flet diff/serialization and
  Flutter drawing separately; style reuse does not remove the full shape rebuild.
  Measure throughput and memory for the native 120,000–1,000,000-session presets.
- Standalone Scroll: actual START/END scrolling, user-position preservation,
  content growth, and native axis behavior.
- Table: native double-click/keyboard ordering; Session tests only verify
  double-tap callback routing.
- Broader visual and interaction coverage for the supported cookbook pages;
  serialized Session checks do not establish client rendering correctness.
- Display scaling and other desktop platforms.

Existing regression commands are in [flet_regression.py](../tests/flet_regression.py),
[flet_table.py](../tests/flet_table.py), [flet_canvas.py](../tests/flet_canvas.py),
and [flet_tabs.py](../tests/flet_tabs.py). Run all with
`env/bin/python -m unittest discover -s tests -p 'flet_*.py' -v`.
Worker-thread tests need normal process socket access for asyncio executor cleanup.
Constructor argument compatibility is checked by
[signature_regression.py](../tests/signature_regression.py); client rendering
and interaction checks above remain pending.
Legacy decorator warnings, metadata, and argument forwarding are checked in
[decorator_signatures.py](../tests/decorator_signatures.py). Flet 1.0.4 requires
Python 3.10+; Python 3.9 is outside this backend's supported runtime.
On 2026-10-27, `flet_regression` and `flet_tabs` passed 32 recording-session tests
on macOS / Python 3.14.8 / Flet 1.0.4. This does not validate native Flutter geometry,
focus, touch or screen-reader behavior. Shared
changes must still pass the [Python 3.9 baseline](pyside6-reference.md#python-39-compatibility).

### Visibility and adaptive layout

- **Unverified:** real Flutter-client focus/cursor/scroll behavior after `.visible(False)` then reappearance. Python control/shell retention is tested; transient client state is not guaranteed.

Adaptive Layout: `on_size_change` wiring and inherited size State are covered by the recording-session tests; verify initial geometry and repeated breakpoint transitions in a real Flutter client.

## Decisions to discuss

Views is deferred by user decision. Reconsider when Flet exposes a suitable
native container; any custom extension would require a separate decision.
See the audited [native visibility handling](https://github.com/flet-dev/flet/blob/v1.0.4/packages/flet/lib/src/extensions/control.dart),
[TabBarView implementation](https://github.com/flet-dev/flet/blob/v1.0.4/packages/flet/lib/src/controls/tabs.dart),
and [disabled inheritance](https://github.com/flet-dev/flet/blob/v1.0.4/packages/flet/lib/src/models/control.dart).

- Canvas images/geometry and Matplotlib/HTML: approve additional dependencies
  before installing them or adding extras.
- Canvas text bounds/anchors: remaining questions are tracked in [wx-progress.md](wx-progress.md).
- Inbound drag/drop: follow the [shared payload/lifecycle contract](https://buganini.github.io/PUI/doc/Reference.html#drop); choose a Flet integration before advertising support.
- Grid spans and vertical Tabs: agree native composition where there
  is no direct mapping.
- Dialogs/Modal: agree the common async/result and cancellation contract.
- Table: agree sizing, additional editors, adapter identity, and paging APIs.
- Desktop integration: decide which PySide6 features should remain unsupported
  in this backend.

## Baseline and process

Use backend `Application`/`PUIView` classes for new code and examples. Keep
deprecated decorators covered by compatibility checks during migration.

Use the current [common reference](https://buganini.github.io/PUI/doc/Reference.html)
and [layout policy](https://buganini.github.io/PUI/doc/Layout.html) as the shared
contract. Historical porting baselines remain in Git history; they must not
reintroduce superseded priorities, sizing or lifecycle behavior.
For Window state, follow the current [initial-only declaration contract](https://buganini.github.io/PUI/doc/Reference.html#window)
instead of the imperative methods introduced in `95e6cff`.
User decisions: target current Flet and use built-in DataTable. Use native Canvas
gestures with documented gaps: pixel wheel fields, zero angular fields, unknown
modifiers, and explicit gesture cancellation. Do not synthesize raw-event parity. The tested runtime
is flet/flet-desktop/flet-web 1.0.4 in env/; see [README](../README.md) for installation.

Work through remaining priorities; skip decisions requiring user input and
continue independent items. Update this document, relevant references, and
Changelog.txt after each change. Validate and commit each completed change.

## Editable ComboBox: accepted design compromise

Editable ComboBox uses a retained TextField and an in-layout candidate list below
it; non-editable ComboBox still uses Dropdown. Matching belongs to application
code. autoexpand controls opening during typing; the arrow and Up/Down can open
choices manually. The native Linux Cookbook was checked with application-defined
`edit_model` matching, real per-character input, mouse selection including an
800ms held press, keyboard selection, Escape, Tab, continued typing and backspace
after selection. Recording-session tests cover retained controls, choices/model
updates, disabled overrides, selection values and switching editability.

**This is an undesired but accepted compromise, not the intended popup design.**
Opening suggestions increases the control's layout height and pushes following
content; compact HBox siblings may also move as their row grows. A constrained
parent may need scrolling to make all content reachable. Flet 1.0.4's public API
does not provide a generic anchored overlay or rendered-control position query.
The tested native Dropdown lost its menu/focus on dynamic option updates; its
only exposed imperative method is focus(), which did not solve this. A fixed-size
Stack prototype could handle pointer input only inside its host bounds and could
not anchor reliably in arbitrary PUI containers. Do not reintroduce those
workarounds into the reusable control. An anchored overlay remains future work,
likely requiring a Flet extension and a separate user decision.

Remaining checks/gaps:

- Real IME composition, screen readers, touch/mobile and macOS/Windows.
- Long/wrapped candidate labels, large lists and scrolling to a keyboard-highlighted
  item outside the visible portion of the list.
- Arbitrary background clicks outside the ComboBox host: actual focus changes
  dismiss suggestions, but a click that leaves the editor focused can leave the
  list open. The public on_tap_outside notification has no target information;
  retaining focus there prevents held candidate clicks from being lost.
- Flet Web runtime interaction checks for the integrated control; the native Linux
  Cookbook checks do not establish browser coverage.
- Native parameter customizations: editable .ui is now a TextField, so Dropdown-only
  `.flet(...)` parameters do not apply; shared PUI styles and disabled still apply.

Implementation references:
- [Flutter RawAutocomplete](https://api.flutter.dev/flutter/widgets/RawAutocomplete-class.html):
  shared field controller/focus node and separate options builder/view.
- [Flutter Stack clipping and hit testing](https://api.flutter.dev/flutter/widgets/Stack/clipBehavior.html):
  disabling clipping does not enlarge the hit-test region.
- [flutter_typeahead](https://pub.dev/packages/flutter_typeahead):
  suggestions overlay with independent open/close and retained field focus.
- [Flet 1.0.4 AutoComplete source](https://github.com/flet-dev/flet/blob/v1.0.4/packages/flet/lib/src/controls/auto_complete.dart):
  native focus wiring and fixed substring matching.
