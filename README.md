# Install
```
pip install QPUIQ
```

# Example
## Code
```python
import PUI
PUI.BACKEND = "PySide6"
from PUI import State
from PUI.generic import *

data = State()
class Example(Window):
    def __init__(self):
        super().__init__(title="blah", size=(640,480))
        data.var = 50

    def content(self):
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

# Progress
* State
    * ~~Update Trigger~~
    * ~~Binding~~
    * List/Dict and Lazy UI
* Verify Nested View
* Adapters
    * Split Application/Window
    * ~~Label~~
    * ~~Button~~
    * ~~TextField~~
    * Layout
        * ~~HBox~~
        * ~~VBox~~
        * ZBox
        * Grid
            * Row
            * Column
    * Canvas
        * ~~Text~~
        * ~~Line~~
        * Rect
        * Arc
        * Image
        * ...
    * Table
    * Tree
    * Scrollbar
* Better DOM syncer
    * Prevent unnecessary nested update
    * Trace Event Source (TextField) and prevent udpate it DOM Sync
    * update() -> sync()/inflate()/update()
