# Standalone examples

These small applications demonstrate PUI declarations, State bindings, layout and
integration with other libraries. The Python modules are included in the package;
run them with `python -m PUI.examples.<name>` from any directory after installation.
For an interactive collection of component demos, use the [cookbook](../cookbook/).

## Getting started

Install the backend you want to use, then run an example:

```shell
python -m pip install 'QPUIQ[pyside6]'
python -m PUI.examples.hello_world
python -m PUI.examples.generic_textfield PySide6
python -m PUI.examples.generic_list PySide6
```

Other backend extras are `QPUIQ[wx]`, `QPUIQ[flet]`, `QPUIQ[textual]` and
`QPUIQ[web]`. For Tkinter, install `QPUIQ` and use a Python installation with Tk
support. See [installation](../../README.md#installation) for platform requirements.

Most `generic_*` examples accept a case-sensitive backend name as their first
argument. **Pass it explicitly:** omitting it randomly selects one of that
example's backends, which might not be installed. The table below lists the
choices implemented by each example's launcher, not a guarantee of feature parity.
The `generic_*` launchers do not accept `web` or `pyodide`; use `grid_sizing`,
`dual_backend` or the browser cookbook for browser examples.

```shell
python -m PUI.examples.generic_dict tkinter
python -m PUI.examples.generic_list wx
python -m PUI.examples.generic_timelineview textual
```

## State and basic controls

| Example | What to try | Backend choices |
| --- | --- | --- |
| [hello_world.py](hello_world.py) | Open a window containing a Label; the smallest Application example. | PySide6 only |
| [generic_minimal.py](generic_minimal.py) | Change a counter with +/− and watch the number of declared Labels change. | PySide6, wx, tkinter, flet, textual |
| [generic_textfield.py](generic_textfield.py) | Edit a bound TextField or use +/− to update the same State value and Label. | PySide6, wx, tkinter, flet, textual |
| [generic_list.py](generic_list.py) | Push/pop entries and rotate their order in a scrollable list; item IDs keep identity across reordering. | PySide6, wx, tkinter, flet, textual |
| [generic_dict.py](generic_dict.py) | Add/remove dictionary entries and click an entry to change its value. | PySide6, tkinter, flet, textual |
| [generic_timelineview.py](generic_timelineview.py) | Observe a clock refreshed by TimelineView every half second. | PySide6, tkinter, flet, textual |

## Layout, drawing and development

| Example | Purpose | Backend choices / extra dependency |
| --- | --- | --- |
| [grid_sizing.py](grid_sizing.py) | Resize a form with Label/Label/TextField rows, spanning toolbars, a nested Grid and Spacers. | PySide6, web, wx, tkinter, textual; defaults to PySide6 |
| [generic_canvas.py](generic_canvas.py) | Use +/− to move text and change a line drawn on Canvas. | PySide6, tkinter, flet |
| [generic_multiwindows.py](generic_multiwindows.py) | Declare two Windows. Use PySide6 or tkinter to see separate native windows; flet and textual have single-window backend constraints. | Launcher accepts PySide6, tkinter, flet, textual |
| [generic_hotreload.py](generic_hotreload.py) | A periodically refreshed clock for experimenting with edits while the app is running. The source also contains a Reloadium-specific hook. | PySide6, tkinter, flet, textual; install `QPUIQ[reload]` for PUI's jurigged integration |
| [generic_memtest.py](generic_memtest.py) | Exercise bound controls and inspect the displayed RSS value and console callbacks. This is a manual diagnostic, not a memory-leak assertion. | PySide6, wx, tkinter, flet, textual; requires `psutil` |
| [dump.py](dump.py) | Print declaration trees for nested nodes, loops and a single node; no window is opened. | Framework only |

Run the Grid example with either a native backend or Web:

```shell
python -m PUI.examples.grid_sizing PySide6
python -m PUI.examples.grid_sizing web
python -m PUI.examples.grid_sizing web --bind 127.0.0.1:8080
```

Web defaults to `127.0.0.1:0`, letting the OS choose a free port; open the printed
URL. The example uses passthru mode. Inspect how editor columns receive extra
width while label columns remain content-sized, including when a child spans
multiple columns. See [Grid sizing policy](../../doc/Layout.html#grid-sizing)
for the shared rules.

For hot-reload experiments, work in a source checkout and edit the example's
`content()` while it runs. For the memory diagnostic:

```shell
python -m pip install psutil
python -m PUI.examples.generic_memtest PySide6
```

## PySide6 and Web sharing State

[dual_backend.py](dual_backend.py) runs PySide6 on the main thread and Web on a
background thread in the same process, sharing both UI declarations and one
State object.

```shell
python -m pip install 'QPUIQ[pyside6,web]'
python -m PUI.examples.dual_backend
```

Open the printed Web URL. Edit text, increment the counter or hover over the
curve in either UI. The cursor is stored as a sample index, so each backend can
map it to its own Canvas dimensions rather than sharing pixel coordinates.
Closing the desktop window stops the Web server and joins its thread. The
example does not synchronize simultaneous State edits from different threads.

The example also accepts `--wstunnel-url`, `--wstunnel-token` and
`--wstunnel-bind`. The relay bind defaults to `tcp://127.0.0.1:0`; relay setup and
Unix socket options are described in the [Web reverse tunnel reference](../../doc/web-reference.md#reverse-tunnel).

## Library and native-widget integrations

These dependencies are separate from the `cookbook` extra. Install only those
needed for the example you want to run.

| Example | Purpose | Requirements |
| --- | --- | --- |
| [bleak_list.py](bleak_list.py) | Scan Bluetooth LE advertisements in a background thread and display device address, name and RSSI through reusable DeviceView instances. | PySide6, `bleak`, an available Bluetooth adapter and OS Bluetooth permissions |
| [pyside6_feedparser.py](pyside6_feedparser.py) | Select an RSS feed, browse entries and display the selected entry's HTML in a second scrolling pane. | PySide6, `feedparser`, network access to the selected feed |
| [pyside6_interop.py](pyside6_interop.py) | Host a PuiInQt view in an application that creates and runs its own QApplication. | PySide6 only; no backend argument is needed |
| [tkinter_sun_valley.py](tkinter_sun_valley.py) | Apply the Sun Valley dark theme in Application.setup(), after the Tk root exists and before controls are created. | Tk-enabled Python, `sv-ttk` |

```shell
python -m pip install 'QPUIQ[pyside6]' bleak
python -m PUI.examples.bleak_list

python -m pip install 'QPUIQ[pyside6]' feedparser
python -m PUI.examples.pyside6_feedparser

python -m PUI.examples.pyside6_interop

python -m pip install QPUIQ sv-ttk
python -m PUI.examples.tkinter_sun_valley
```

## Running from a checkout

Use an activated virtual environment and an editable install so imports use your
checkout, for example `python -m pip install -e '.[pyside6,web]'` from the repository
root. Add the integration dependencies above as needed.

Before running a Web example from source, build its browser assets with
`make web-build`, or run `.\build.ps1` on Windows to build both Web and Pyodide.
Published packages already include the Web assets. See [browser builds](../../doc/web-reference.md#rebuilding-browser-assets)
for prerequisites and individual build commands.
