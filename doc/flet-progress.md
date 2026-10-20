# flet alignment progress

Autocomplete validation must follow the [shared acceptance criteria](Reference.html#autocomplete-acceptance); unverified cases remain pending, including real IME and platform-specific focus behavior.

This document tracks remaining work against PySide6. Implemented behavior belongs
in [common reference](Reference.html), source, and tests. Remove completed items;
keep outstanding validation and decisions. Do not add temporary artifact paths.
**Missing** means the named behavior has no implementation; **Partial** means
implementation exists but the listed gap remains. Validation items below are
**Unverified**, not missing implementations.

## Missing or incomplete behavior

| Priority | Area | State | Remaining work |
| --- | --- | --- | --- |
| P1 | HVBox / VHBox | Unverified | Row/Column switching is tested with the recording transport; verify geometry and cursor/scroll behavior in a native Flutter client. Client-only state resets are an accepted limitation documented in the reference |
| P1 | Views | Deferred | Flet 1.0.4 lacks an exposed IndexedStack/Offstage equivalent. Native visibility removes Flutter widgets; TabBarView permits swiping unless its children are also disabled. Await native support for programmatic-only switching with retained page state; the user chose to defer this adapter |
| P1 | Canvas raw input parity | Partial | Middle-button dragging, extra/simultaneous buttons, wheel modifiers and angular deltas are unavailable in the current native gesture API; native timing/cancellation differs from Qt |
| P1 | Window keyboard | Missing | Wire `.keypress` and map keys/modifiers to the common event contract |
| P1 | VBox alignment | Unverified | Native Column START and Row CENTER match the alignment defaults; verify client geometry and expansion |
| P1 | Styles | Partial | Propagate inherited container fonts to descendants |
| P2 | Canvas images | Missing | Implement `ImageResource.load/crop/scale`, `loadImage`, and `drawImage`, including source rectangles and opacity; dependency decision pending |
| P2 | Canvas text/HiDPI | Partial | Implement text height clipping, resolve shared anchor/bounds behavior, and report actual display density instead of the fixed 1.0 fallback |
| P2 | Canvas geometry | Missing | Implement `drawShapely`; optional dependency decision pending |
| P2 | Tabs | Partial | Add Side.RIGHT/Side.LEFT placement after choosing a native layout approach |
| P2 | Grid/Splitter | Missing | Implement Grid row/column spans and Splitter; layout approach pending |
| P2 | Dialogs/Modal | Missing | Implement file/directory dialogs, messages, Confirm/Prompt, and Modal; common async/result contract pending |
| P2 | Table | Partial | Resolve `autofit=False`, additional editor types, stable adapter row identities, and large-data paging; current headers scroll with data and Qt selection parity is absent |
| P2 | Tree | Missing | Implement Tree/TreeNode and adapter reconciliation with selection/expansion preservation |
| P3 | Menus/toolbars | Missing | Implement MenuBar/Menu/MenuAction and ToolBar/ToolBarAction |
| P3 | Desktop integration | Missing | Decide scope for MdiArea/MdiSubWindow, multiple windows, and native-widget interop |
| P3 | Rich content | Missing | Implement HTML rendering and MatplotlibCanvas; dependency decisions pending |
| Shared | Drag/drop | Missing | Define the common payload/lifecycle contract before backend implementation |

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
Python 3.10+; Python 3.9 is outside this backend's supported runtime. Shared
changes must still pass the [Python 3.9 baseline](../README.md#python-39-compatibility).

## Decisions to discuss

Views is deferred by user decision. Reconsider when Flet exposes a suitable
native container; any custom extension would require a separate decision.
See the audited [native visibility handling](https://github.com/flet-dev/flet/blob/v1.0.4/packages/flet/lib/src/extensions/control.dart),
[TabBarView implementation](https://github.com/flet-dev/flet/blob/v1.0.4/packages/flet/lib/src/controls/tabs.dart),
and [disabled inheritance](https://github.com/flet-dev/flet/blob/v1.0.4/packages/flet/lib/src/models/control.dart).

- Canvas images/geometry and Matplotlib/HTML: approve additional dependencies
  before installing them or adding extras.
- Canvas text bounds/anchors and drag/drop: shared contract choices are tracked
  in [wx-progress.md](wx-progress.md).
- Grid spans, Splitter, and vertical Tabs: agree native composition where there
  is no direct mapping.
- Dialogs/Modal: agree the common async/result and cancellation contract.
- Table: agree sizing, additional editors, adapter identity, and paging APIs.
- Desktop integration: decide which PySide6 features should remain unsupported
  in this backend.

## Baseline and process

Use backend `Application`/`PUIView` classes for new code and examples. Keep
deprecated decorators covered by compatibility checks during migration.

PySide6 baseline for all modules: `2b06235fdbbec6e09195ce714c117b03677c6303`.
`95e6cff` supersedes Window/Modal state, Base size policies/redraw guards,
ComboBox invalid selection, and TextField edit caching. `6722caa` supersedes
ProgressBar fractional range conversion. `9a3b142` supersedes ComboBox free-text
handling, `675e831` editor/quit lifecycle, and `b9e3ad5` Tabs placement. Record
newer component SHAs only when adopting later behavior.
For Window state, follow the current [initial-only declaration contract](Reference.html#window)
instead of the imperative methods introduced in `95e6cff`.
PySide6 Table reference: `0cb3fe0a186af08ef9b91b0f22a6743218daedc8`, superseded
by `df4cbac` for adapter refresh.

User decisions: target current Flet and use built-in DataTable. Use native Canvas
gestures with documented gaps: pixel wheel fields, zero angular fields, unknown
modifiers, and explicit gesture cancellation. Do not synthesize raw-event parity. The tested runtime
is flet/flet-desktop/flet-web 1.0.4 in env/; see [README](../README.md) for installation.

Work through remaining priorities; skip decisions requiring user input and
continue independent items. Update this document, relevant references, and
Changelog.txt after each change. Validate and commit each completed change.

## Visibility checks

- **Unverified:** real Flutter-client focus/cursor/scroll behavior after `.visible(False)` then reappearance. Python control/shell retention is tested; transient client state is not guaranteed.

Adaptive Layout: `on_size_change` wiring and inherited size State are covered by the recording-session tests; verify initial geometry and repeated breakpoint transitions in a real Flutter client.

Native ComboBox uses Dropdown with enable_filter=False; matching belongs to application code. Native search/highlighting follows autoexpand. Flutter popup positioning, focus retention and keyboard selection still need broader native-platform checks; the flag does not guarantee that a popup stays open while refocusing the editor.

Reliable expansion and focus during application-defined candidate updates remain pending. Standalone Dropdown option replacement disrupted continued input; TextField with a separate results list retained focus. SearchBar supports dynamic candidates but opens a separate search view and does not restore editor focus after selection.

Linux Flet 1.0.4 native-window and Chrome experiments also tested reopening
Dropdown after replacing options. Manually reopening showed the new candidates,
but typing with the menu open did not continue until the editor was clicked again.
Calling the public `focus()` method after each options update did not restore
continuous typing in the native-window test. Dropdown exposes no public menu
open/close methods (the Dart method handler only supports `focus`), so an automatic
close/reopen cycle cannot currently be implemented through that API. IME and
cross-platform behavior remain unverified; this experiment does not resolve the
integration gap.

A Stack prototype must not be treated as a usable ComboBox overlay: with a
field-height Stack and `clip_behavior=NONE`, candidates paint outside its bounds
but ordinary Flutter pointer hit testing cannot select them. Browser accessibility
semantics allowed selection in a separate test, so that result did not establish
normal pointer support. Scoped KeyboardListener handling can dismiss the prototype
with Escape without changing the draft. Anchoring, normal mouse selection,
blur dismissal, IME and integration remain unresolved.

Flet 1.0.4 AutoComplete has a working native overlay and Escape dismissal in
Linux Chrome, but its Dart `optionsBuilder` performs whole-query substring
matching and suppresses empty-query suggestions. The Python API does not expose
a replacement matcher. A custom Flutter extension or an in-layout candidate
list requires a packaging/behavior decision before integration.

Dynamically setting each suggestion's `key` to include the current query while
keeping its label in `value` does not resolve this in Flet 1.0.4: Linux Chrome
tests with both slow and fast typing sent the correct four `tai tok` candidates,
but the native menu stayed closed. Refocusing did not refresh it; deleting the
last character made the previous keys match and displayed the candidates.
Updating `suggestions` alone is therefore insufficient for live custom matching.
Forcing text changes or recreating the editor is not an accepted workaround
because caret, focus and composition must be preserved.

Implementation references:
- [Flutter RawAutocomplete](https://api.flutter.dev/flutter/widgets/RawAutocomplete-class.html):
  shared field controller/focus node and separate options builder/view.
- [Flutter Stack clipping and hit testing](https://api.flutter.dev/flutter/widgets/Stack/clipBehavior.html):
  disabling clipping does not enlarge the hit-test region.
- [flutter_typeahead](https://pub.dev/packages/flutter_typeahead):
  suggestions overlay with independent open/close and retained field focus.
- [Flet 1.0.4 AutoComplete source](https://github.com/flet-dev/flet/blob/v1.0.4/packages/flet/lib/src/controls/auto_complete.dart):
  native focus wiring and fixed substring matching.
