# Backend validation — 2026-10-28

Runtime: macOS 26.5 arm64, Python 3.14.8, wxPython 4.3.2 / wxWidgets
3.3.4 Cocoa, Tk 9.1.0, Flet 1.0.4, Textual 8.2.8 and Matplotlib 3.11.2.
These results establish the listed checks on this runtime, not cross-platform
visual or input parity.

## Automated results

Run Python suites from the repository with `PYTHONPATH=tests:. env/bin/python
-m unittest <modules> -v`. Native suites require an active desktop session.

| Backend | Modules | Result |
| --- | --- | --- |
| wx | wx_canvas, wx_splitter, wx_views, wx_tabs, wx_tree, wx_table, wx_drop, wx_modal, divider_native.WxDividerTests | 41 passed with native Cocoa widgets |
| Tkinter | tkinter_canvas, tkinter_splitter, tkinter_views, tkinter_tabs, tkinter_table, tkinter_lifecycle, tkinter_sizing, tkinter_modal, divider_native.TkDividerTests | 43 passed after fixing Views initialization |
| Web | web_bind, web_lifecycle, web_ipc, web_passthru, web_startup, web_server, web_auth, web_auth_expiry, web_sessions, web_owners, web_tunnel, web_forwarded | 122 passed; 1 Linux-only Landlock test skipped |
| Web protocol | web_capacity, web_protocol, web_canvas_diff | 17 passed after correcting MessagePack array expectations |
| Web spawn wrapper | web_spawn | 29 intentionally skipped on macOS; native server tests already use spawn |
| Flet | flet_regression, flet_canvas, flet_tabs, flet_table, flet_splitter | 57 passed with recording sessions; separate client checks below |
| Textual | textual_regression, textual_views, textual_tabs, textual_table, textual_splitter, textual_grid, textual_combobox | 49 passed with headless Pilot; real terminal protocols remain pending |
| Pyodide bridge | pyodide_runtime | 9 passed in host Python; separate browser check below |

Tk Views initially failed all four tests: syncing a virtual child refreshes its
ancestors while sibling pages may still have no native widget. `_show_view()`
now skips those pages; the final Views sync maps the selected page. Rerunning
Views, Tabs, Modal and lifecycle together passed all 16 tests, including retained
edits, keyed reorder/removal and model replacement.

The capacity test initially compared decoded arrays with Python tuples.
MessagePack decodes both tuples and lists as lists. Normalize expected arrays
recursively while retaining exact value, dictionary and sequence-order checks;
no production wire format was changed.

Web tests exercise real local server processes, TCP/Unix binds, ownership and
permissions, startup, shutdown, SIGTERM, authentication and session handling.
Tunnel tests mock the external process; they do not validate a live relay.
Windows Proactor behavior, frozen applications, installed wheel assets and
long-running process/handle counts remain separate checks.

## Native Flet desktop

A real Flutter desktop window was exercised with a bound TextField, reversible
HBox, weighted Matplotlib line chart and retained Modal:

- The chart rendered its curve, axes and title; this does not establish the
  six-panel clipping/image/text comparison or Canvas capture support.
- Typing committed the value and updated the bound label.
- HBox reversal visibly reversed the controls.
- Modal opened, closed through its content button, fired open/close callbacks
  and reopened. Escape did not close it, including after Tab focus traversal.
- After the combined modal/reversal sequence, the editor appeared empty while
  the bound label retained its text. Isolate this client-state retention issue
  before claiming focus/value retention across that sequence.

Nested dialog focus, IME, touch, accessibility, broader geometry, and other
platforms remain pending. Recording-session success alone does not verify them.

## Actual Pyodide browser

Built with `node browser-client/build-pyodide.mjs` and served `dist/pyodide`
through a local static HTTP server. Chrome loaded the actual Python worker and
became interactive in approximately 3 seconds. The 20-page construction loop,
Button callback, editable ComboBox selection/free-text, Table edits/choices,
retained Views, timers and Blob images passed. HeavyCanvas hover at 1,000–30,000
sessions, zoom and command deltas passed, followed by worker restart, epoch
change, Blob cleanup and duplicate-message rejection. No WebSocket or codec
requests were made. The full `tests/pyodide_browser.cjs` run passed.

Corrected outdated selectors for the editable ComboBox and a Table cell prefix.
Restart checks now wait for renderer readiness rather than assuming the initial
cookbook page contains “Row 1”; the epoch-change assertion remains in place.

This run does not establish Firefox/Safari/mobile support, real IME or long-term
background-tab/resource behavior. See the backend progress notes for remaining
checks rather than treating host-Python bridge tests as browser validation.
