# Declarative Components
|Generic|PySide6|flet|tkinter|textual|wx|
|-------|-------|----|-------|-------|--|
|[Application](#application)|QApplication|Page|Tk|App|App|
|[Window](#window)|QMainWindow|✓(Single)|Toplevel|✓(Single)|Frame|
|[HBox](#hbox)|QHBoxLayout|Row|Frame(grid)|Horizontal|BoxSizer|
|[VBox](#vbox)|QVBoxLayout|Column|Frame(grid)|Vertical|BoxSizer|
|[Grid](#grid)|QGridLayout|-|||GridBagSizer|
|[Spacer](#spacer)|QSpacerItem|✓|✓|✓|✓|
|[Divider](#divier)|✓||||StaticLine|
|[Label](#label)|QLabel|Text|Label|Label/Button|StaticText|
|[Button](#button)|QPushButton|ElevatedButton|Button|Button|Button|
|[Checkbox](#checkbox)|QCheckBox|Checkbox|Checkbutton|Checkbox|Checkbox
|[RadioButton](#radiobutton)|QRadioButton|Radio|Radiobutton|RadioButton|RadioButton
|[Canvas](#canvas)|✓(QWidget)|Canvas|Canvas||✓(Panel)
|[TextField](#textfield)|QLineEdit|TextField|Entry|Input|TextCtrl|
|[ProgressBar](#progressbar)|QProgressBar|ProgressBar|Progressbar|ProgressBar|Gauge|
|[Scroll](#scroll)|QScrollArea|✓|✓|ScrollableContainer|ScrolledPanel|
|[Text](#text)|QLabel|Text|Label|Text|
|[Html](#html)|QLabel|⚠ Text|⚠ Label|⚠ Text|
|[MarkDown](#markdown)|QLabel|Markdown|⚠ Label|Markdown|
|[ComboBox](#combobox)|QComboBox|-|-|-|Combobox
|[Table](#table)|QTableView|-|-|-|
|[Tree](#tree)|QTreeView|-|-|-|
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
[Example](cookbook/dialog.py)
|Generic|PySide6|flet|tkinter|textual|wx|
|-------|-------|----|-------|-------|--|
|OpenDirectory|QFileDialog.getExistingDirectory|-|-|-|DirDialog|
|OpenFile|QFileDialog.getOpenFileName|-|-|-|FileDialog|
|OpenFiles|QFileDialog.getOpenFileNames|-|-|-|FileDialog|
|SaveFile|QFileDialog.getSaveFileName|-|-|-|FileDialog|
|Information|QMessageBox|-|-|-|MessageBox|
|Warning|QMessageBox|-|-|-|MessageBox|
|Critical|QMessageBox|-|-|-|MessageBox|
|Confirm|QMessageBox|-|-|-|MessageDialog|
|Prompt|QInputDialog|-|-|-|TextEntryDialog|
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

# Callback Interface
All callback interfaces accept an event object as the first argument. Other args/kwargs will be passed through to the callback function.

For example
```python
def button_cb(event, data):
    print(data)

Button("button").click(button_cb, 1)
```
will invoke
```
button_cb(event, 1)
```
when the event is emitted.

## Event Object
### click
* nothing for now
### dblclick
* .x, .y: double click position
### mousedown
* .x, .y: mouse down position
### mouseup
* .x, .y: mosue up position
### mousemove
* .x, .y: mouse move position
### wheel
* .x, .y: wheel position
* .x_delta, .y_delta: pixel delta
* .h_delta, .v_delta: angle delta
### input
Triggered when typing in `TextField`
* .value: text in edit buffer
### change
Triggered when editing is finished in `TextField`
* .value: new value

# Declarative Components
## Common Modifiers
* .layout(width=320, height=240, weight=1, padding=, margin=)
* .style(color=0xFF0000, bgColor=0x333333, fontSize=16, fontWeight="bold", fontFamily="Arial")
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

[Example](cookbook/modal.py)
``` python
Modal(model[,offValue=None][,title=str][,size=(w,h)][,maximize=bool][,fullscreen=bool])
```

## HBox
Horizontal Linear Layout Container

[Example](cookbook/hbox.py)
``` python
HBox()
```

## VBox
Vertical Linear Layout Container

[Example](cookbook/tab.py)
``` python
VBox()
```

## Grid
Grid Layout Container

[Example](cookbook/grid.py)
``` python
with Grid():
    Text("A").grid(row=0, column=0)
    Text("B").grid(row=1, column=0, rowspan=2)
```

## Spacer
Spacer inside linear layout containers

[Example](cookbook/hbox.py)
``` python
with HBox():
    Text("Left")
    Spacer()
    Text("Right")
```

## Divider
Divider inside linear layout containers

[Example](cookbook/vbox.py)
``` python
with VBox():
    Text("Top")
    Divider()
    Text("Bottom")
```

## Scroll
Scrollable container

[Example](cookbook/scroll.py)
``` python
with Scroll().layout(weight=1).scrollY(Scroll.END):
    with VBox():
        for i in range(100):
            Label(f"Row {i+1}")
```

## Button
Single line clickable text with button appearance

[Example](cookbook/button.py)
``` python
Button(text).click(callback, *cb_args, **cb_kwargs)
```

### Callbacks
* .click


## Label
Single line clickable text

[Example](cookbook/label.py)
``` python
Label(text).click(callback, *cb_args, **cb_kwargs)
```

### Callbacks
* .click

## Text
Multiple line text viewer

[Example](cookbook/text.py)
``` python
Text(text)
```

## Html
HTML viewer (only supported by PySide6 backend)

[Example](cookbook/text.py)
``` python
Html(html)
```

## Markdown
Markdown viewer (not supported by tkinter backend)

[Example](cookbook/text.py)
``` python
Markdown(md)
```

## Combobox
Editable Dropdown List
[Example](cookbook/combobox.py)
``` python
with ComboBox(editable=True, index_model=state("index"), text_model=state("text")):
    ComboBoxItem("Item 1")
    ComboBoxItem("Item 2")
    ComboBoxItem("Item 3")
```

## TextField
Single line text editor

[Example](cookbook/textfield.py)
``` python
TextField(binding, edit_buffer_binding=None)
```

### Callbacks
* .input: edit buffer changed
* .change: editing finished


## ProgressBar
Linear progress indicator

[Example](cookbook/progressbar.py)
``` python
ProgressBar(progress `0-1`)
```

## Checkbox
[Example](cookbook/checkbox.py)
``` python
Checkbox(label, model)
```

### Callbacks
* .click

## RadioButton
[Example](cookbook/radiobutton.py)
``` python
RadioButton(label, value, model)
```

## Canvas
[Example](cookbook/canvas.py)
``` python
def painter(canvas):
    canvas.drawText(x, y, text, w=None, h=None, size=12, color=None, rotate=0, anchor=Anchor.LEFT_TOP)
    canvas.drawLine(x1, y1, x2, y2, color=0xFF0000, width=1)
    canvas.drawPolyline([x1, y2, ..., xn, yn], color=0xFF0000, width=1)
    canvas.drawRect(x1, y1, x2, y2, fill=0xFF0000, stroke=0x00FF00, width=1)
    canvas.drawShapely(shape, fill=0xFF0000, stroke=0x00FF00, width=1)

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
[Example](cookbook/tab.py)

## Table

Table widget

[Example with TableNode](cookbook/table.py)

``` python
with Table():
    with TableNode():
        TableNode("A1")
        TableNode("A2")
    with TableNode():
        TableNode("B1")
        TableNode("B2")
```

[Example with adapter](cookbook/table_adapter.py)
``` python
Table(adapter)
```

## Tree

Single column tree widget

*There should be a `TreeTable` for multi/fixed-column trees and a `NestedTable` for variable-column trees, but they have not been implemented yet*

[Example with TableNode](cookbook/tree.py)

``` python
with Tree():
    with TreeNode("Root"):
        with TreeNode("Sub 1"):
            TreeNode("Sub 1-1")
            TreeNode("Sub 1-2")
        TreeNode("Sub 2")
        with TreeNode("Sub 3"):
            TreeNode("Sub 3-1")
```

[Example with adapter](cookbook/tree_adapter.py)
``` python
Tree(adapter)
```

## Interop
### QtInPui
Wrapper for embedding native widget instance into PUI

Currently only supported by PySide6 backend

[Example](cookbook/widget.py)


### PuiInQt
Wrapper for embedding PUI view into existing QT view hierarchy

Currently only supported by PySide6 backend

[Example](examples/pyside6_interop.py)
