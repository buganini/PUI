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
|Splitter|QSplitter|-|-|-|
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

# Declarative Components
## Common Modifiers
* .layout(width=320, height=240, weight=1, padding=, margin=)
* .style(color=0xFF0000, bgColor=0x0, fontSize=16, fontWeight="bold", fontFamily="Arial")
* .qt(HorizontalPolicy=, VerticalPolicy=, SizeConstraint=, StyleSheet={})
* .flet(k=v)

## Application
Top level element of an application
```
Application()
```

## Window
flet and textual backends only support single window
```
Window([title=str][,size=(w,h)][,maximize=bool][,fullscreen=bool])
```

## Modal
Modal window

[Example](https://github.com/buganini/PUI/blob/main/cookbook/modal.py)
```
Modal(model[,offValue=None][,title=str][,size=(w,h)][,maximize=bool][,fullscreen=bool])
```

## HBox
Horizontal Linear Layout Container

[Example](https://github.com/buganini/PUI/blob/main/cookbook/hbox.py)
```
HBox()
```

## VBox
Vertical Linear Layout Container

[Example](https://github.com/buganini/PUI/blob/main/cookbook/tab.py)
```
VBox()
```

## Grid
Grid Layout Container

[Example](https://github.com/buganini/PUI/blob/main/cookbook/grid.py)
```
with Grid():
    Text("A").grid(row=0, column=0)
    Text("B").grid(row=1, column=0, rowspan=2)
```

## Spacer
Spacer inside linear layout containers

[Example](https://github.com/buganini/PUI/blob/main/cookbook/hbox.py)
```
with HBox():
    Text("Left")
    Spacer()
    Text("Right")
```

## Scroll
Scrollable container

[Example](https://github.com/buganini/PUI/blob/main/cookbook/scroll.py)
```
with Scroll().layout(weight=1).scrollY(Scroll.END):
    with VBox():
        for i in range(100):
            Label(f"Row {i+1}")
```

## Button
Single line clickable text with button appearance

[Example](https://github.com/buganini/PUI/blob/main/cookbook/button.py)
```
Button(text).click(callback, *cb_args, **cb_kwargs)
```

## Label
Single line clickable text

[Example](https://github.com/buganini/PUI/blob/main/cookbook/label.py)
```
Label(text).click(callback, *cb_args, **cb_kwargs)
```

## Text
Multiple line text viewer

[Example](https://github.com/buganini/PUI/blob/main/cookbook/text.py)
```
Text(text)
```

## Html
HTML viewer (only supported by PySide6 backend)

[Example](https://github.com/buganini/PUI/blob/main/cookbook/text.py)
```
Html(html)
```

## Markdown
Markdown viewer (not supported by tkinter backend)

[Example](https://github.com/buganini/PUI/blob/main/cookbook/text.py)
```
Markdown(md)
```

## TextField
Single line text editor

[Example](https://github.com/buganini/PUI/blob/main/cookbook/textfield.py)
```
TextField(binding)
```
## ProgressBar
Linear progress indicator

[Example](https://github.com/buganini/PUI/blob/main/cookbook/progressbar.py)
```
ProgressBar(progress `0-1`)
```

## Checkbox
[Example](https://github.com/buganini/PUI/blob/main/cookbook/checkbox.py)
```
Checkbox(label, model)
```

## RadioButton
[Example](https://github.com/buganini/PUI/blob/main/cookbook/radiobutton.py)
```
RadioButton(label, value, model)
```

## Canvas
[Example](https://github.com/buganini/PUI/blob/main/cookbook/canvas.py)
```
def painter(canvas):
    canvas.drawText(x, y, text)
    canvas.drawLine(x1, y1, x2, y2, color=0xFF0000, width=2)
    canvas.drawPolyline([x1, y2, ..., xn, yn], color=0xFF0000, width=2)

Canvas(painter)
```

## Tabs and Tab
[Example](https://github.com/buganini/PUI/blob/main/cookbook/tab.py)

## Table

Table widget

[Example](https://github.com/buganini/PUI/blob/main/cookbook/table.py)
```
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
