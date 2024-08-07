# Declarative Components
|Generic|PySide6|flet|tkinter|textual|wx|
|-------|-------|----|-------|-------|--|
|[Application](#application)|QApplication|Page|Tk|App|App|
|[Window](#window)|QMainWindow|✓(Single)|Toplevel|✓(Single)|Frame|
|[HBox](#hbox)|QHBoxLayout|Row|Frame(grid)|Horizontal|BoxSizer|
|[VBox](#vbox)|QVBoxLayout|Column|Frame(grid)|Vertical|BoxSizer|
|[Grid](#grid)|QGridLayout|-|||GridBagSizer|
|[Spacer](#spacer)|QSpacerItem|✓|✓|✓|✓|
|[Label](#label)|QLabel|Text|Label|Label/Button|StaticText|
|[Button](#button)|QPushButton|ElevatedButton|Button|Button|Button|
|[Checkbox](#checkbox)|QCheckBox|Checkbox|Checkbutton|Checkbox|
|[RadioButton](#radiobutton)|QRadioButton|Radio|Radiobutton|RadioButton|
|[Canvas](#canvas)|✓(QWidget)|Canvas|Canvas|-|
|[TextField](#textfield)|QLineEdit|TextField|Entry|Input|TextCtrl|
|[ProgressBar](#progressbar)|QProgressBar|ProgressBar|Progressbar|ProgressBar|
|[Scroll](#scroll)|QScrollArea|✓|✓|ScrollableContainer|
|[Text](#text)|QLabel|Text|Label|Text|
|[Html](#html)|QLabel|⚠ Text|⚠ Label|⚠ Text|
|[MarkDown](#markdown)|QLabel|Markdown|⚠ Label|Markdown|
|Combobox|QComboBox|-|-|-|
|ComboboxItem|✓|-|-|-|
|[Table](#table)|QTableView|-|-|-|
|[Tabs](#tabs-and-tab)|QTabWidget|Tabs|Notebook|Tabs|
|[Tab](#tabs-and-tab)|✓|Tab|✓|✓|
|MenuBar|QMenuBar|-|-|-|
|Menu|QMenu|-|-|-|
|MenuAction|QAction|-|-|-|
|ToolBar|QToolBar|-|-|-|
|ToolBarAction|QToolBarAction|-|-|-|
|MdiArea|QMdiArea|-|-|-|
|MdiSubWindow|QMdiSubWindow|-|-|-|
|[Splitter](#splitter)|QSplitter|-|-|-|
|[MatplotlibCanvas](#matplotlibcanvas)|FigureCanvas||||
|[Modal](#modal)|✓|-|-|-|
|[(Interop)](#interop)|[QtInPui](#qtinpui)|-|-|-|
|[(Interop)](#interop)|[PuiInQt](#puiinqt)|-|-|-|

# Imperative Dialogs
|Generic|PySide6|flet|tkinter|textual|
|-------|-------|----|-------|-------|
|OpenDirectory|QFileDialog.getExistingDirectory|-|-|-|
|OpenFile|QFileDialog.getOpenFileName|-|-|-|
|OpenFiles|QFileDialog.getOpenFileNames|-|-|-|
|SaveFile|QFileDialog.getSaveFileName|-|-|-|
|Information|QMessageBox|-|-|-|
|Warning|QMessageBox|-|-|-|
|Critical|QMessageBox|-|-|-|
|Confirm|QMessageBox|-|-|-|
|Prompt|QInputDialog|-|-|-|
___

# Decorators
## @PUIApp
``` python
@PUIApp
def Example():
    ...
```
is equivalent to
``` python
class Example(Application):
    def content(self):
        ...
```

## @PUI
``` python
@PUI
def SubView():
    ...
```
is equivalent to
``` python
class SubView(PUIView):
    def content(self):
        ...
```


# Declarative Components
## Common Modifiers
* .layout(width=320, height=240, weight=1, padding=, margin=)
* .style(color=0xFF0000, bgColor=0x0, fontSize=16, fontWeight="bold", fontFamily="Arial")
* .qt(HorizontalPolicy=, VerticalPolicy=, SizeConstraint=, StyleSheet={})
* .flet(k=v)

## Application
Top level element of an application
``` python
Application().qt(Style="fusion")
```

## Window
flet and textual backends only support single window
``` python
Window([title=str][,size=(w,h)][,maximize=bool][,fullscreen=bool])
```

## Modal
Modal window

[Example](https://github.com/buganini/PUI/blob/main/cookbook/modal.py)
``` python
Modal(model[,offValue=None][,title=str][,size=(w,h)][,maximize=bool][,fullscreen=bool])
```

## HBox
Horizontal Linear Layout Container

[Example](https://github.com/buganini/PUI/blob/main/cookbook/hbox.py)
``` python
HBox()
```

## VBox
Vertical Linear Layout Container

[Example](https://github.com/buganini/PUI/blob/main/cookbook/tab.py)
``` python
VBox()
```

## Grid
Grid Layout Container

[Example](https://github.com/buganini/PUI/blob/main/cookbook/grid.py)
``` python
with Grid():
    Text("A").grid(row=0, column=0)
    Text("B").grid(row=1, column=0, rowspan=2)
```

## Spacer
Spacer inside linear layout containers

[Example](https://github.com/buganini/PUI/blob/main/cookbook/hbox.py)
``` python
with HBox():
    Text("Left")
    Spacer()
    Text("Right")
```

## Scroll
Scrollable container

[Example](https://github.com/buganini/PUI/blob/main/cookbook/scroll.py)
``` python
with Scroll().layout(weight=1).scrollY(Scroll.END):
    with VBox():
        for i in range(100):
            Label(f"Row {i+1}")
```

## Button
Single line clickable text with button appearance

[Example](https://github.com/buganini/PUI/blob/main/cookbook/button.py)
``` python
Button(text).click(callback, *cb_args, **cb_kwargs)
```

### Callbacks
* .click: clicked


## Label
Single line clickable text

[Example](https://github.com/buganini/PUI/blob/main/cookbook/label.py)
``` python
Label(text).click(callback, *cb_args, **cb_kwargs)
```

### Callbacks
* .click: clicked

## Text
Multiple line text viewer

[Example](https://github.com/buganini/PUI/blob/main/cookbook/text.py)
``` python
Text(text)
```

## Html
HTML viewer (only supported by PySide6 backend)

[Example](https://github.com/buganini/PUI/blob/main/cookbook/text.py)
``` python
Html(html)
```

## Markdown
Markdown viewer (not supported by tkinter backend)

[Example](https://github.com/buganini/PUI/blob/main/cookbook/text.py)
``` python
Markdown(md)
```

## TextField
Single line text editor

[Example](https://github.com/buganini/PUI/blob/main/cookbook/textfield.py)
``` python
TextField(binding, edit_buffer_binding=None)
```

### Callbacks
* .input: edit buffer changed
* .change: editing finished


## ProgressBar
Linear progress indicator

[Example](https://github.com/buganini/PUI/blob/main/cookbook/progressbar.py)
``` python
ProgressBar(progress `0-1`)
```

## Checkbox
[Example](https://github.com/buganini/PUI/blob/main/cookbook/checkbox.py)
``` python
Checkbox(label, model)
```

### Callbacks
* .click: clicked

## RadioButton
[Example](https://github.com/buganini/PUI/blob/main/cookbook/radiobutton.py)
``` python
RadioButton(label, value, model)
```

## Canvas
[Example](https://github.com/buganini/PUI/blob/main/cookbook/canvas.py)
``` python
def painter(canvas):
    canvas.drawText(x, y, text)
    canvas.drawLine(x1, y1, x2, y2, color=0xFF0000, width=2)
    canvas.drawPolyline([x1, y2, ..., xn, yn], color=0xFF0000, width=2)
    canvas.drawRect(x1, y1, x2, y2, fill=0xFF0000, stroke=0x00FF00, width=2)

Canvas(painter)
```

### Callbacks
* .dblclick
* .mousedown
* .mouseup
* .mousemove
* .wheel

## MatplotlibCanvas
``` python
data = [(0,0), (1,3), (2,2)]
def plot(figure, data):
    figure.clear()
    sp = figure.add_subplot(111)
    sp.axes.plot([d[0] for d in data], [d[1] for d in data])

MatplotlibCanvas(plot, data)
```

## Splitter
Splitter(vertical=False)
``` python
with Splitter():
    Label("Left")
    Label("Right")
```

## Tabs and Tab
[Example](https://github.com/buganini/PUI/blob/main/cookbook/tab.py)

## Table

Table widget

[Example](https://github.com/buganini/PUI/blob/main/cookbook/table.py)
``` python
Table(adapter)
```

## Interop
### QtInPui
Wrapper for embedding native widget instance into PUI

Currently only supported by PySide6 backend

[Example](https://github.com/buganini/PUI/blob/main/cookbook/widget.py)


### PuiInQt
Wrapper for embedding PUI view into existing QT view hierarchy

Currently only supported by PySide6 backend

[Example](https://github.com/buganini/PUI/blob/main/examples/pyside6_interop.py)
