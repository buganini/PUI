# What is PUI
PUI is a declarative UI framework with two-way data binding

# Installation
```
pip install QPUIQ
```

# Get Started
## Hello World
```python
# example/hello_world.py

from PUI import State
from PUI.PySide6 import *

class Example(Application):
    def content(self):
        with Window(title="test", size=(640,480)):
            Label("Hellow world")

root = Example()
root.run()
```

## State & Data Binding
```python
# example/generic_minimal.py

from PUI import State
from PUI.PySide6 import *

data = State()
data.var = 0

class QtExample(QtApplication):
    def content(self):
        with QtWindow(title="blah"):
            with QtVBox():
                with QtHBox():
                    QtButton("-", self.on_minus)
                    QtLabel(f"{data.var}")
                    QtButton("+", self.on_plus)

                QtLineEdit(data("var")) # binding

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = QtExample()
root.run()
```

## View Component
```python
# example/bleak_list.py

....

@PUI
def DeviceView(device, advertising_data):
    Label(f"{device.address} {device.name} {advertising_data.rssi}")

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

## Layout & Styling
```python
# example/pyside6_feedparser.py

...
with VBox():
    Label(title).qt(StyleSheet="font-weight:bold") # QT-specific

    with HBox():
        with Scroll():
            with VBox():
                for i,e in enumerate(entries):
                    Label(e.title).click(self.entry_selected, i)
                Spacer()

        with Scroll().layout(weight=1): # Generic Layout Parameter
            if 0 <= selected and selected < len(entries):
                Text(entries[selected].description).qt(StyleSheet="background-color:white; color:black") # QT-specific
...
```

## More Example
See `examples/`

# Backends
## Tier-1
* PySide6
## Lower Priority
* tkinter
    * or https://github.com/rdbende/Sun-Valley-ttk-theme
* PyQt5
* flet
    * no canvas
* urwid (Text Mode)
    * no canvas

# Generic Expression
* Take a look at [PUI/PySide6/\_\_init__.py](https://github.com/buganini/PUI/blob/main/PUI/PySide6/__init__.py)
## Elements
* HBox()
* VBox()
* Spacer()
* Button(text, callback, *cb_args, **cb_kwargs)
* Label(text)
    * .click(callback, *cb_args, **cb_kwargs)
* TextField(binding)
* ProgressBar(progress `0-1`)
* Scroll()
* Canvas
    * CanvasText
    * CanvasLine(x1, y1, x2, y2, color=0xFF0000, width=2)
## Layout
* .layout(width=320, height=240, weight=1)

# Hot Reload
Add these lines to your view file and run with `reloadium`
```python
import reloadium

# reloadium: after_reload
def after_reload(actions):
    PUIView.reload()
```

# TODO
* ~~Use threading.locals() instead of inspect~~
* State
    * ~~Update Trigger~~
    * ~~Binding~~
    * ~~StateList~~
    * ~~StateDict~~
    * Lazy UI?
* StateObject decorator
* Adapters
    * ~~Split Application/Window, multi-windows~~
    * UI Flow
        * Navigation Stack
        * View Router
        * Model Window/Dialog
    * ~~Label~~
    * ~~Button~~
    * ~~TextField~~
    * ~~TimelimeView~~
    * Layout
        * ~~HBox~~
        * ~~VBox~~
        * ZBox
        * Grid
            * Row
            * Column
        * SwiftUI style overlay ??
    * Canvas
        * ~~Text~~
        * ~~Line~~
        * Rect
        * Arc
        * Image
        * ...
    * Table
    * Tree
    * ~~Scrollbar (or as a layout setting)~~
* Better DOM syncer
    * Prevent unnecessary nested update
    * Trace Event Source (TextField) and prevent update it DOM Sync
* Pydantic State