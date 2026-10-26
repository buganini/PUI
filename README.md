# What is PUI
PUI is a reactive/declarative UI framework with two-way data binding.
PUI doesn't do UI itself, it turns imperative UI libraries into reactive/declarative flavor with virtual DOM and aims to maintain interoperability.

[Slides for SciWork 2023](https://speakerdeck.com/buganini/pui-declarative-ui-framework-for-python)

[CPPUI: C++ Version](https://github.com/buganini/CPPUI)

# Features

* [Declarative UI](#hello-world)
* [Reactive state with two-way binding](#state--data-binding)
* Hot Reloading
* [Multiple Backends](#backends)
  * PySide6
  * wxPython
  * Tkinter
  * Flet
  * Textual
  * Pyodide (client-side Python)
  * Web (server-side Python)
    * [Built-in reverse wstunnel integration](doc/web-reference.md#reverse-tunnel)
* [Responsive / Adaptive Layout](#responsive--adaptive-layout)

## Responsive / Adaptive Layout

Adapt to the parent container's available size: switch between rows and columns,
show or hide content at breakpoints, and override layout or style settings.
Desktop and browser backends use logical pixels; Textual has separate cell-based
breakpoints and settings.

```python
# Inside content(), using your selected backend as UI:
with UI.HVBox(minWidth=600, tMinWidth=60):
    UI.Label("Title").style(fontSize=14).wideStyle(900, fontSize=20)
    UI.Button("Save")
```

Grid layouts can also change their column count at breakpoints and automatically
place items while respecting spans.

- [![Reference: Responsive Layout](https://img.shields.io/badge/Reference-Responsive_Layout-526d82?style=flat-square)](https://buganini.github.io/PUI/doc/Reference.html#responsive-layout)
- [![Cookbook: Adaptive Grid](https://img.shields.io/badge/Cookbook-Adaptive_Grid-52796f?style=flat-square)](https://buganini.github.io/PUI/cookbook/cookbook.html#cookbook.page=Adaptive%20Grid)
- [![Cookbook: Adaptive Layout](https://img.shields.io/badge/Cookbook-Adaptive_Layout-52796f?style=flat-square)](https://buganini.github.io/PUI/cookbook/cookbook.html#cookbook.page=Adaptive%20Layout)

# Installation

PUI requires Python 3.9 or newer. Backend packages have their own Python and
platform requirements; the versions available for your interpreter may differ.
The shared framework and PySide6 backend retain Python 3.9 support. Shared changes
must preserve that baseline even when an optional backend requires newer Python.

Choose a backend extra:

```shell
pip install 'QPUIQ[pyside6]'
pip install 'QPUIQ[wx]'
pip install 'QPUIQ[flet]'
pip install 'QPUIQ[web]'
pip install 'QPUIQ[textual]'
```

The `web` extra installs aiohttp, msgpack and zstandard with their dependencies.
Browser JavaScript, CSS and zstd WASM are bundled in the package; no separate npm
install is needed to run the backend.

Install the development/cookbook dependencies with:

```shell
pip install 'QPUIQ[cookbook]'      # Pygments, Matplotlib and Shapely
pip install 'QPUIQ[web,cookbook]'  # Web backend plus cookbook dependencies
```

The `cookbook` extra can be combined with any backend extra. Pip selects dependency
versions compatible with the current Python interpreter, including Python 3.9.

The flet extra installs the current Flet 1.x desktop/web runtime (minimum tested
version: 1.0.4, requiring Python 3.10 or newer). Table support uses its built-in
DataTable, including Dropdown choices and dialog editing; no table extension
is required.

For tkinter, install `QPUIQ` and use a Python build with Tk support:

```shell
pip install QPUIQ
python -c "import tkinter"
```

The optional `QPUIQ[tkinter]` spelling installs the same packages; its extra is
empty because Tk is supplied by Python or the operating system.
Some Linux distributions provide Tk support separately as
`python3-tk`; an existing virtual environment uses its base Python's native
support. wxPython can also require platform-native GTK/build dependencies.

For the framework alone, install `QPUIQ`. Optional development tools:

```shell
pip install 'QPUIQ[reload]'  # Hot reload via jurigged
pip install 'QPUIQ[landlock]'  # Optional Linux filesystem allowlists; see doc/landlock.md
pip install textual-dev # Textual development tools
```

When working from this checkout, use the project environment:

```shell
python3 -m venv env
env/bin/python -m pip install -e '.[pyside6,flet,textual,cookbook]'
# Add .[wx] when wxPython is available for the platform.
# Add reload to enable hot reload, e.g. -e '.[web,cookbook,reload]'.
```

## AI development

Install an optional agent SDK alongside your backend (Python 3.10+):

```sh
pip install 'QPUIQ[pyside6,codex]'   # or QPUIQ[web,claude]
python -m PUI
```

The launcher checks the selected provider's CLI login, asks for a backend and
Python class name, creates an empty application, prints its command and runs it.
Existing applications can use `app.start(codex={})` / `claude={}` for CLI login,
or pass `{"key": "API_KEY"}`. Optional `model` and `effort` entries select the provider settings. Web gets a browser sidebar; PySide6, wx, Flet and
tkinter get an AI window supervising a restartable application child.
See [AI development](doc/ai-reference.md) for permissions, State preservation and
`make pyside6_codex` / `pyside6_claude` and corresponding wx/Flet/tkinter/Web targets.

# Get Started

Define applications by subclassing the backend's `Application`, and reusable
views by subclassing its `PUIView`. Put UI declarations in `content()`, initialize
local state in `setup()`, and use member functions as event handlers.

## Hello World
```python
# example/hello_world.py
import PUI.PySide6 as UI

class Example(UI.Application):
    def content(self):
        with UI.Window(title="test", size=(320,240)):
            UI.Label("Hello world")

root = Example()
root.run()
```
![Hello World](screenshots/hello_world.png)

[![Reference: Declarative Components](https://img.shields.io/badge/Reference-Declarative_Components-526d82?style=flat-square)](https://buganini.github.io/PUI/doc/Reference.html#declarative-components)

## State & Data Binding
```python
# example/generic_textfield.py
from PUI.PySide6 import *

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        data.var = 0

    def content(self):
        with Window(title="blah"):
            with VBox():
                with HBox():
                    Button("-").click(self.on_minus)
                    Label(f"{data.var}")
                    Button("+").click(self.on_plus)

                TextField(data("var")) # binding

    def on_minus(self, event):
        data.var -= 1

    def on_plus(self, event):
        data.var += 1

root = Example()
root.run()
```
![State & Data Binding](screenshots/pyside6_textfield.png)

## View Component
```python
# example/bleak_list.py

....

class DeviceView(PUIView):
    def __init__(self, device, advertising_data):
        super().__init__()
        self.device = device
        self.advertising_data = advertising_data

    def content(self):
        Label(f"{self.device.address} {self.device.name} {self.advertising_data.rssi}")

class GUI(Application):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def content(self):
        with Window(title="BLE List"):
            with VBox():
                Label(f"Found {len(self.state.scanned_devices)} devices")
                for device, advertising_data in self.state.scanned_devices:
                    DeviceView(device, advertising_data)

....
```
![View Component](screenshots/bleak_list.png)

## Layout & Styling

PUI handles normal widget sizing automatically. Each component supplies a
preferred size and expansion policy appropriate to the widget and its position
in an `HBox` or `VBox`; for example, a `TextField` uses the available horizontal
space while retaining its native height, and a `Spacer` consumes flexible space.
Application code normally does not need to assign control dimensions just to
make a layout fit.

Use `.layout(width=..., height=..., weight=..., padding=..., margin=...)` when a
design needs an explicit size, a particular share of flexible space, or custom
spacing. PUI translates these semantic rules to each backend's native layout
system, so exact pixel sizes can still vary with the toolkit, platform, font,
and theme.

Web resolves flexible space on the parent container's main axis: width in HBox,
height in VBox. Positive weights take priority over automatic expansion;
`weight=0` preserves the widget's preferred size. Setting only Canvas width or
height leaves its other axis flexible.

- [![Reference: Layout](https://img.shields.io/badge/Reference-Layout-526d82?style=flat-square)](https://buganini.github.io/PUI/doc/Reference.html#common-modifiers)

```python
# example/pyside6_feedparser.py

...
with VBox():
    Label(title).qt(StyleSheet={"font-weight":"bold"}) # QT-specific

    with HBox():
        with Scroll():
            with VBox():
                for i,e in enumerate(entries):
                    Label(e.title).click(self.entry_selected, i)
                Spacer()

        with Scroll().layout(weight=1): # Generic Layout Parameter
            if 0 <= selected and selected < len(entries):
                (Text(entries[selected].description)
                    .layout(padding=10) # Generic Layout Parameter
                    .qt(StyleSheet={"background-color":"white", "color":"black"})) # QT-specific
...
```
![Layout & Styling](screenshots/feed_parser_padding.png)


## Cookbook

The cookbook is included in the package. Install a backend and its example dependencies, then run it from any directory:

```shell
python -m pip install 'QPUIQ[pyside6,cookbook]'
python -m PUI.cookbook PySide6
```

The `cookbook` extra includes Pygments for the code viewer, Matplotlib for the
MatplotlibCanvas example, and Shapely 2.x or newer for DrawShapely.
[cookbook/requirements.txt](PUI/cookbook/requirements.txt) remains an equivalent
dependency list. Choose a different backend extra as needed; for Tkinter,
use `'QPUIQ[cookbook]'` with a Tk-enabled Python. Backend support still determines
which examples are available. Hot reload and Textual development tools are optional.

Styled examples, Grid tiles, Canvas and Matplotlib use
muted blues, terracotta, greens and warm creams, with color values written directly in
each example.

The code viewer uses a fixed dark Monokai palette. Backends without HTML support
show plain text with the same dark background and light foreground.

See [Canvas](https://buganini.github.io/PUI/cookbook/cookbook.html#cookbook.page=Canvas) for drawing examples and
[HeavyCanvas](https://buganini.github.io/PUI/cookbook/cookbook.html#cookbook.page=HeavyCanvas) for a large interactive chart.

Use `make pyodide` to run the cookbook with Python in the browser, loaded from a
fixed official CDN version. See the [Pyodide reference](doc/pyodide-reference.md)
for the GitHub Pages entry, build and deployment instructions.

![Cookbook 1](screenshots/cookbook1.png)
![Cookbook 2](screenshots/cookbook2.png)

`python -m PUI.cookbook textual`

Use `make textual` to run the Textual cookbook. For development mode, install
`textual-dev` and use `make textual_dev`.

![Cookbook textual](screenshots/cookbook_textual.png)

`python -m PUI.cookbook flet`
![Cookbook flet](screenshots/cookbook_flet.png)

`python -m PUI.cookbook tkinter`

The Tkinter cookbook tries Sun Valley light when the external `sv-ttk` package is installed;
otherwise it uses `classic`. Theme loading lives in the cookbook's `setup()`.

![Cookbook tkinter](screenshots/cookbook_tkinter.png)

# Backends

The progress documents below track backend alignment, remaining work and checked
runtime versions.

* PySide6 (reference implementation) — [Python 3.9 compatibility](doc/pyside6-reference.md#python-39-compatibility)
* wxPython — [Progress](doc/wx-progress.md)
* Flet — [Progress](doc/flet-progress.md)
* Tkinter — [Progress](doc/tkinter-progress.md); external [Sun Valley theme](https://github.com/rdbende/Sun-Valley-ttk-theme).
  Install `sv-ttk`, then run `python -m PUI.examples.tkinter_sun_valley` for a [dark theme example](PUI/examples/tkinter_sun_valley.py).
* [Web](doc/web-reference.md) (Python runs on the server) — [Progress](doc/web-progress.md).
  `make web` builds the browser bundle and serves the cookbook at [http://localhost:8866/pui/](http://localhost:8866/pui/).
  From a Git checkout, install Node.js with npm/npx, then run `make web-build`; it automatically installs the locked frontend dependencies and builds the bundle without starting the server. `make build` builds both Web and Pyodide without starting servers. On Windows, run `.\build.ps1` in PowerShell to install the locked dependencies and build both without Make (Python 3.9+ is also required). `make publish` runs `web-build` first. See [browser builds](doc/web-reference.md#rebuilding-browser-assets).
* [Pyodide](doc/pyodide-reference.md) (Python runs in the browser) — [Progress](doc/pyodide-progress.md).
  `make pyodide-build` builds the static site in `dist/pyodide`;
  `make pyodide` builds and serves the cookbook at [http://localhost:8868/cookbook/cookbook.html](http://localhost:8868/cookbook/cookbook.html).
* Textual (terminal UI; no Canvas) — [Progress](doc/textual-progress.md)

# Documents

[![Documentation: Index](https://img.shields.io/badge/Documentation-Index-526d82?style=flat-square)](doc/README.md)

API and layout references, backend guides, examples and remaining work.

# Used by
* https://github.com/buganini/Kikakuka

# TODO
* Dump with layout parameters and add test cases
* [ISSUE] flet layout sizing (cookbook scroll example)
* nested state trigger
    * set state in PUIView __init__
    * set state in setup() ?
* Tabs(`tabposition`)
* Lazy List
* UI Flow
    * Navigation Stack
    * View Router
    * Model Window/Dialog
* Layout
    * SwiftUI style overlay ??
* Canvas
    * Arc
    * ...
* State with Pydantic support?
