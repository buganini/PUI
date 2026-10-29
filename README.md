# What is PUI
PUI is a reactive/declarative UI framework with two-way data binding.
PUI doesn't do UI itself, it turns imperative UI libraries into reactive/declarative flavor with virtual DOM and aims to maintain interoperability.

[Slides for SciWork 2023](https://speakerdeck.com/buganini/pui-declarative-ui-framework-for-python)

[CPPUI: C++ Version](https://github.com/buganini/CPPUI)

# Features

* [Declarative UI](#hello-world)
* [Reactive state with two-way binding](#state--data-binding)
* Hot Reloading
* [Multiple Backends](PUI/doc/README.md#backend-guides-and-remaining-work)
  * PySide6
  * wxPython
  * Tkinter
  * Flet
  * Textual
  * [Pyodide (client-side Python)](https://buganini.github.io/PUI/cookbook/cookbook.html)
  * Web (server-side Python)
    * [Run alongside a desktop backend with shared state](PUI/examples/dual_backend.py)
    * [Built-in reverse wstunnel integration](PUI/doc/web-reference.md#reverse-tunnel)
* [Responsive / Adaptive Layout](#responsive--adaptive-layout)

# Documents

[![Try it: Browser Cookbook](https://img.shields.io/badge/Try_it-Browser_Cookbook-52796f?style=flat-square)](https://buganini.github.io/PUI/cookbook/cookbook.html)

[![Documentation: Index](https://img.shields.io/badge/Documentation-Index-526d82?style=flat-square)](PUI/doc/README.md)

API and layout references, backend guides, examples and remaining work.

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
pip install 'QPUIQ[landlock]'  # Optional Linux filesystem allowlists; see PUI/doc/landlock.md
pip install textual-dev # Textual development tools
```

When working from this checkout, use the project environment:

```shell
python3 -m venv env
env/bin/python -m pip install -e '.[pyside6,flet,textual,cookbook]'
# Add .[wx] when wxPython is available for the platform.
# Add reload to enable hot reload, e.g. -e '.[web,cookbook,reload]'.
```

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

[![Cookbook: State & Binding](https://img.shields.io/badge/Cookbook-State_%26_Binding-52796f?style=flat-square)](https://buganini.github.io/PUI/cookbook/cookbook.html#cookbook.page=State%20%26%20Binding)

### State transactions across threads

State operations are synchronized across threads. Use `with state:` for compound
updates or consistent multi-field reads, and keep native widget access on its UI thread:

```python
with data:
    data.count += 1
```

[![Reference: State Transactions](https://img.shields.io/badge/Reference-State_Transactions-526d82?style=flat-square)](https://buganini.github.io/PUI/doc/Reference.html#state-transactions)

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

PUI sizes components from their content and distributes extra space using shared,
per-axis expansion priorities. Labels and buttons normally fit their content;
text fields expand horizontally, while Canvas and MatplotlibCanvas can expand on
both axes. Nested containers carry their children's expansion needs upward.
Grid applies the same priorities to rows and columns, including spanning cells.

Use `.layout()` to adjust sizes and spacing:

- `width` / `height` set desired dimensions and stop automatic expansion on that axis.
- `minWidth` / `minHeight` set minimum sizes without stopping expansion.
- Positive `weight` takes precedence on an HBox/VBox's main axis and shares space
  proportionally with other weighted siblings. In Grid it applies to both axes.
  `weight=0` disables expansion on those axes.
- `padding` and `margin` control spacing.

Use `.style()` for shared colors and typography, or `.qt(StyleSheet={...})` for
Qt-specific styling such as borders and other QSS properties. Textual uses `.tLayout()` and
`.tStyle()` for terminal-cell dimensions and terminal styling. Native fonts,
themes and size hints can still produce different exact dimensions; component
support and styling limits are documented in the reference.

```python
# Inside content(), with components imported from your selected backend:
with VBox().layout(padding=12).tLayout(padding=1):
    Label("Details").style(fontWeight=FontWeight.Bold).tStyle(
        fontWeight=FontWeight.Bold,
    )
    Label("Qt-specific details").qt(StyleSheet={
        "font-weight": "bold", "border-bottom": "1px solid #888",
    })
    with HBox():
        Text("Notes").layout(weight=1, minWidth=180).tLayout(minWidth=20)
        Text("Preview").layout(weight=2, padding=10).style(
            color=0x1C2A30, bgColor=0xFFF7E6,
        ).tLayout(padding=1).tStyle(color=0x1C2A30, bgColor=0xFFF7E6)
```

- [![Reference: Layout](https://img.shields.io/badge/Reference-Layout-526d82?style=flat-square)](https://buganini.github.io/PUI/doc/Layout.html)
- [![Reference: Layout and Style Modifiers](https://img.shields.io/badge/Reference-Layout_%26_Style_Modifiers-526d82?style=flat-square)](https://buganini.github.io/PUI/doc/Reference.html#common-modifiers)

## Responsive / Adaptive Layout

Adapt to the parent container's available size: switch between rows and columns,
show or hide content at breakpoints, and override layout or style settings.
Desktop and browser backends use logical pixels; Textual has separate cell-based
breakpoints and settings.

```python
# Inside content(), with components imported from your selected backend:
with HVBox(minWidth=600, tMinWidth=60):
    Label("Title").style(fontSize=14).wideStyle(900, fontSize=20)
    Button("Save")
```

Grid layouts can also change their column count at breakpoints and automatically
place items while respecting spans.

- [![Reference: Responsive Layout](https://img.shields.io/badge/Reference-Responsive_Layout-526d82?style=flat-square)](https://buganini.github.io/PUI/doc/Reference.html#responsive-layout)
- [![Cookbook: Adaptive Grid](https://img.shields.io/badge/Cookbook-Adaptive_Grid-52796f?style=flat-square)](https://buganini.github.io/PUI/cookbook/cookbook.html#cookbook.page=Adaptive%20Grid)
- [![Cookbook: Adaptive Layout](https://img.shields.io/badge/Cookbook-Adaptive_Layout-52796f?style=flat-square)](https://buganini.github.io/PUI/cookbook/cookbook.html#cookbook.page=Adaptive%20Layout)

# Cookbook

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
fixed official CDN version. See the [Pyodide reference](PUI/doc/pyodide-reference.md)
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

# AI Development

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
See [AI development](PUI/doc/ai-reference.md) for permissions, State preservation and
`make pyside6_codex` / `pyside6_claude` and corresponding wx/Flet/tkinter/Web targets.

# Used by
* https://github.com/buganini/Kikakuka
