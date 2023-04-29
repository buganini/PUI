# Install
```
pip install QPUIQ
```

# Example
## Code
```python
from PUI import State
# from PUI.tkinter import *
from PUI.PySide6 import *
# from PUI.Qt5 import *
# from PUI.flet import *

data = State()
data.var = 50
class Example(Application):
    def content(self):
        with Window(title="blah", size=(640,480)):
            with VBox():
                with Canvas():
                    CanvasText(data.var, data.var/2, f"blah {data.var}")
                    CanvasLine(data.var, data.var, data.var*2, data.var*3)
                with HBox():
                    Button("-", self.on_minus)
                    Label(f"{data.var}")
                    Button("+", self.on_plus)

    def on_minus(self):
        data.var -= 1

    def on_plus(self):
        data.var += 1

root = Example()
root.run()
```

## UI
![Qt Canvas Example](https://github.com/buganini/PUI/raw/main/screenshots/pyside6_canvas.gif)

## DOM
``` swift
Example {
  QtVBox {
    QtCanvas {
      QtCanvasText {

      },
      QtCanvasLine {

      }
    },
    QtHBox {
      QtButton {

      },
      QtLabel {

      },
      QtButton {

      }
    }
  }
}
```

# More Example
See `examples/*.py`

# Planned Backends
* tkinter
* PyQt5
* PySide6
* flet
* urwid (Text Mode)

# Generic Expression
## Elements
* HBox()
* VBox()
* Button(text, callback)
* Label(text)
* TextField(binding)
* ProgressBar(progress `0-1`)
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

# Progress
* ~~Use threading.locals() instead of inspect~~
* State
    * ~~Update Trigger~~
    * ~~Binding~~
    * ~~StateList~~
    * ~~StateDict~~
    * Lazy UI?
* Passing state to subview
* StateObject decorator
* Adapters
    * ~~Split Application/Window, multi-windows~~
    * Navigation Stack
    * View Router
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
    * Scrollbar (or as a layout setting)
* Better DOM syncer
    * Prevent unnecessary nested update
    * Trace Event Source (TextField) and prevent udpate it DOM Sync
    * update() -> sync()/inflate()/update() ?
* Pydantic State