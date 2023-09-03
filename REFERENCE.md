# Declarative Components
|Generic|PySide6|flet|tkinter|textual|
|-------|-------|----|-------|-------|
|[Application](#application)|QApplication|Page|Tk|App|
|[Window](#window)|QMainWindow|✓(Single)|Toplevel|✓(Single)|
|[HBox](#hbox)|QHBoxLayout|Row|Frame(grid)|Horizontal|
|[VBox](#vbox)|QVBoxLayout|Column|Frame(grid)|Vertical|
|[Spacer](#spacer)|QSpacerItem|✓|✓|✓|
|[Label](#label)|QLabel|Text|Label|Label/Button|
|[Button](#button)|QPushButton|ElevatedButton|Button|Button|
|[Checkbox](#checkbox)|QCheckBox|Checkbox|Checkbutton|Checkbox|
|[RadioButton](#radiobutton)|QRadioButton|Radio|Radiobutton|RadioButton|
|[Canvas](#canvas)|✓(QWidget)|Canvas|Canvas|-|
|[TextField](#textfield)|QLineEdit|TextField|Entry|Input|
|[ProgressBar](#progressbar)|QProgressBar|ProgressBar|Progressbar|ProgressBar|
|[Scroll](#scroll)|QScrollArea|✓|✓|ScrollableContainer|
|[Text](#text)|QLabel|Text|Label|Text|
|[Html](#html)|QLabel|⚠ Text|⚠ Label|⚠ Text|
|[MarkDown](#markdown)|QLabel|Markdown|⚠ Label|Markdown|
|Combobox|QComboBox|-|-|-|
|ComboboxItem|✓|-|-|-|
|Table|QTableView|-|-|-|
|Tabs|QTabWidget|Tabs|Notebook|Tabs|
|Tab|✓|Tab|✓|✓|
|MenuBar|QMenuBar|-|-|-|
|Menu|QMenu|-|-|-|
|MenuAction|QAction|-|-|-|
|MdiArea|QMdiArea|-|-|-|
|MdiSubWindow|QMdiSubWindow|-|-|-|
|Splitter|QSplitter|-|-|-|
|Modal|✓(QWidget)|-|-|-|
|(Wrapper)|`QtWrapper`|-|-|-|

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

## HBox
Horizontal Linear Layout Container
```
HBox()
```

## VBox
Vertical Linear Layout Container
```
VBox()
```

## Spacer
Spacer inside linear layout containers
```
with HBox():
    Text("Left")
    Spacer()
    Text("Right")
```

## Scroll
Scrollable container
```
with Scroll().layout(weight=1).scrollY(Scroll.END):
    with VBox():
        for i in range(100):
            Label(f"Row {i+1}")
```

## Button
Single line clickable text with button appearance
```
Button(text).click(callback, *cb_args, **cb_kwargs)
```

## Label
Single line clickable text
```
Label(text).click(callback, *cb_args, **cb_kwargs)
```

## Text
Multiple line text viewer
```
Text(text)
```

## Html
HTML viewer (only supported by PySide6 backend)
```
Html(html)
```

## Markdown
Markdown viewer (not supported by tkinter backend)
```
Markdown(md)
```

## TextField
Single line text editor
```
TextField(binding)
```
## ProgressBar
Linear progress indicator
```
ProgressBar(progress `0-1`)
```

## Checkbox
```
Checkbox(label, model)
```

## RadioButton
```
RadioButton(label, value, model)
```

## Canvas
```
def painter(canvas):
    canvas.drawText(x, y, text)
    canvas.drawLine(x1, y1, x2, y2, color=0xFF0000, width=2)
    canvas.drawPolyline([x1, y2, ..., xn, yn], color=0xFF0000, width=2)

Canvas(painter)
```