# What is PUI
PUI is a reactive/declarative UI framework with two-way data binding.
PUI doesn't do UI itself, it turns imperative UI libraries into reactive/declarative flavor with virtual DOM and aims to maintain interoperability.

[Slides for SciWork 2023](https://speakerdeck.com/buganini/pui-declarative-ui-framework-for-python)

[CPPUI: Experimental C++ Version](https://github.com/buganini/CPPUI)

# Installation
```
pip install QPUIQ
```

# Get Started
## Hello World
```python
# example/hello_world.py
from PUI.PySide6 import *

@PUIApp
def Example():
    with Window(title="test", size=(320,240)):
        Label("Hello world")

root = Example()
root.run()
```
![Hello World](screenshots/hello_world.png)

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

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = Example()
root.run()
```
![State & Data Binding](screenshots/pyside6_textfield.png)

## View Component
```python
# example/bleak_list.py

....

@PUI # View Component
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
![View Component](screenshots/bleak_list.png)

## Layout & Styling
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


## Canvas
```python
# example/generic_canvas.py

from PUI.PySide6 import *

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        data.var = 50

    def content(self):
        with Window(title="blah", size=(640,480)):
            with VBox():
                Canvas(self.painter, data.var)
                with HBox():
                    Button("-").click(self.on_minus)
                    Label(f"{data.var}").layout(weight=1)
                    Button("+").click(self.on_plus)

    @staticmethod
    def painter(canvas, var):
        canvas.drawText(var, var/2, f"blah {var}")
        canvas.drawLine(var, var, var*2, var*3, color=0xFFFF00)

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = Example()
root.run()
```
![Canvas](screenshots/pyside6_canvas.gif)

## Cookbook
`python -m cookbook PySide6` (requires pygments for syntax highlight)

![Cookbook 1](screenshots/cookbook1.png)
![Cookbook 2](screenshots/cookbook2.png)

`python -m cookbook textual`
![Cookbook textual](screenshots/cookbook_textual.png)

`python -m cookbook flet`
![Cookbook flet](screenshots/cookbook_flet.png)

`python -m cookbook tkinter`
![Cookbook tkinter](screenshots/cookbook_tkinter.png)

# Hot Reload
``` shell
pip install jurigged
```
Then PUI will take care of view update [(code)](https://github.com/buganini/PUI/blob/main/PUI/__init__.py#L11)


# Backends
## Tier-1
* PySide6
## Lower Priority
* wx
* tkinter
    * or https://github.com/rdbende/Sun-Valley-ttk-theme
* flet
* textual (Text Mode)
    * no canvas

# Components
[Reference](REFERENCE.md)

# Used by
* https://github.com/buganini/kikit-ui
* https://github.com/solvcon/modmesh

# TODO
* Merge node and view
* Dump with layout parameters and add test cases
* [Toga](https://beeware.org/project/projects/libraries/toga/)
* [ISSUE] textual layout sizing (cookbook scroll example)
* [ISSUE] flet layout sizing (cookbook scroll example)
* nested state trigger
    * set state in PUIView __init__
    * set state in setup() ?
* Tabs(`tabposition`)
* Lazy List
* StateObject decorator
* UI Flow
    * Navigation Stack
    * View Router
    * Model Window/Dialog
* Layout
    * ZBox
    * SwiftUI style overlay ??
* Canvas
    * Rect
    * Arc
    * Image
    * ...
* Table
* Tree
* Dialog
* State with Pydantic support?