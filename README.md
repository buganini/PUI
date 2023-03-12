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
        with VBox() as scope:
            with Canvas() as canvas:
                CanvasText(data.var, data.var/2, f"blah {data.var}")
                CanvasLine(data.var, data.var, data.var*2, data.var*3)
            with HBox() as scope:
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
![Qt Canvas Example](https://github.com/buganini/PUI/raw/main/screenshots/qt_canvas.png)

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
    * ~~Label~~
    * ~~Button~~
    * Layout
        * ~~HBox~~
        * ~~VBox~~
    * Canvas
        * ~~Text~~
        * ~~Line~~
        * Rect
        * Arc
        * Image
        * ...
    * Table
    * Tree
    * TextField
    * Scrollbar
* Better DOM syncer
* Prevent unnecessary nested update