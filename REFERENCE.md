# Declarative Components
|Generic|PySide6|flet|tkinter|textual|wx|
|-------|-------|----|-------|-------|--|
|[Application](#application)|QApplication|Page|Tk|App|App|
|[Window](#window)|QMainWindow|✓(Single)|Toplevel|✓(Single)|Frame|
|[HBox](#hbox)|QHBoxLayout|Row|Frame(grid)|Horizontal|BoxSizer|
|[VBox](#vbox)|QVBoxLayout|Column|Frame(grid)|Vertical|BoxSizer|
|[Grid](#grid)|QGridLayout|-|Frame(grid)||GridBagSizer|
|[Stack](#stack)|QStackedLayout (StackAll)|Stack|-|-|-|
|[Image](#image)|QLabel|Image|-|-|StaticBitmap|
|[Spacer](#spacer)|QSpacerItem|✓|✓|✓|✓|
|[Divider](#divider)|✓||ttk.Separator||StaticLine|
|[Label](#label)|QLabel|Text|Label|Label/Button|StaticText|
|[Button](#button)|QPushButton|Button|Button|Button|Button|
|[Checkbox](#checkbox)|QCheckBox|Checkbox|Checkbutton|Checkbox|Checkbox
|[RadioButton](#radiobutton)|QRadioButton|Radio|Radiobutton|RadioButton|RadioButton
|[Canvas](#canvas)|✓(QWidget)|Canvas|Canvas||✓(Panel)
|[TextField](#textfield)|QLineEdit|TextField|Entry|Input|TextCtrl|
|[ProgressBar](#progressbar)|QProgressBar|ProgressBar|Progressbar|ProgressBar|Gauge|
|[Scroll](#scroll)|QScrollArea|✓|✓|ScrollableContainer|ScrolledPanel|
|[Text](#text)|QLabel|Text|Label|Text|StaticText/TextCtrl|
|[Html](#html)|QLabel|⚠ Text|⚠ Label|⚠ Text|HtmlWindow (subset)|
|[MarkDown](#markdown)|QLabel|Markdown|⚠ Label|Markdown|
|[ComboBox](#combobox)|QComboBox|Dropdown|ttk.Combobox|-|Combobox
|[Table](#table)|QTableView|DataTable|-|-|wx.grid.Grid|
|[Tree](#tree)|QTreeView|-|-|-|DataViewCtrl|
|[Tabs](#tabs-and-tab)|QTabWidget|Tabs|Notebook|Tabs|Notebook|
|[Tab](#tabs-and-tab)|✓|Tab|✓|✓|Panel|
|MenuBar|QMenuBar|-|-|-|MenuBar|
|Menu|QMenu|-|-|-|Menu|
|MenuAction|QAction|-|-|-|MenuItem|
|ToolBar|QToolBar|-|-|-|
|ToolBarAction|QToolBarAction|-|-|-|
|MdiArea|QMdiArea|-|-|-|
|MdiSubWindow|QMdiSubWindow|-|-|-|
|[Splitter](#splitter)|QSplitter|-|-|-|
|[MatplotlibCanvas](#matplotlibcanvas)|FigureCanvas||||
|[Modal](#modal)|✓|-|-|-|
|[(Interop)](#interop)|[QtInPui](#qtinpui)|-|-|-|
|[(Interop)](#interop)|[PuiInQt](#puiinqt)|-|-|-|

wx MenuBar contains Menu declarations; Menu contains nested Menu or MenuAction.
`.trigger(callback, *args, **kwargs)` invokes the callback without an event
argument, matching PySide6. Labels and callbacks update during reconciliation.
Toolbar, MDI, rich Markdown, and native interop remain pending design
choices. Remaining work is listed in [wx progress](doc/wx-progress.md).

# Imperative Dialogs
[Example](cookbook/dialog.py)
|Generic|PySide6|flet|tkinter|textual|wx|
|-------|-------|----|-------|-------|--|
|OpenDirectory|QFileDialog.getExistingDirectory|-|askdirectory|-|DirDialog|
|OpenFile|QFileDialog.getOpenFileName|-|askopenfilename|-|FileDialog|
|OpenFiles|QFileDialog.getOpenFileNames|-|askopenfilenames|-|FileDialog|
|SaveFile|QFileDialog.getSaveFileName|-|asksaveasfilename|-|FileDialog|
|Information|QMessageBox|-|showinfo|-|MessageBox|
|Warning|QMessageBox|-|showwarning|-|MessageBox|
|Critical|QMessageBox|-|showerror|-|MessageBox|
|Confirm|QMessageBox|-|askyesno|-|MessageDialog|
|Prompt|QInputDialog|-|askstring|-|TextEntryDialog|
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

On wx, import `PUI` and `PUIView` from `PUI.wx` to schedule reactive redraws on
the wx GUI queue. Redraw bursts are coalesced; removed views ignore queued work.
Native widgets are reused during reconciliation and destroyed with their owner.

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

wx supports four-sided `padding` in top/right/bottom/left order for children
of HBox/VBox/Grid. Width and height set native minimum-size hints; weights are
recomputed during reconciliation, including zero. Generic font size/family,
font weight (`"bold"` or normal), foreground, and background apply to wx controls;
omitting a style on the next declaration restores its original native value.

## Application
Top level element of an application
``` python
Application().qt(Style="fusion")
```

## Window

`maximize=` and `fullscreen=` describe initial state. For wx and PySide6,
changing those constructor arguments in a later declaration does not alter a
live window. Use `.maximize(enabled=True)` or `.fullscreen(enabled=True)` to
change state imperatively; `False` clears that state. The methods return the
node and also accept calls before native creation. PySide6 Modal follows the
same contract. Tkinter Window implements the same methods; Flet Window implements the same methods using Page.window.

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

Tkinter uses native grid positions/spans and four-sided padding. Occupied rows
and columns stretch uniformly; unused axes reset their weights after replacement.
Divider uses ttk.Separator, vertical in HBox and horizontal otherwise.

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

wx and PySide6 expose `.scrollX(pos)` and `.scrollY(pos)`: positive values are
logical-pixel offsets from the start; negative values are offsets from the end.
`Scroll.END` is negative zero. wx preserves a manual position on redraw and
follows the end when content grows. Axis options are `None` (as needed), `True`
(always show), or `False` (disabled). wx uses native one-pixel scroll units.

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

Flet preserves native text selection. Ordinary labels dispatch clicks through
their existing Container; `selectable=True` labels use Text.on_tap. Callbacks
refresh or clear on redraw and commit focused editors before running.

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
HTML viewer (PySide6 and the native wx HTML subset; wx does not implement browser CSS)

[Example](cookbook/text.py)
``` python
Html(html)
```

## Markdown
Markdown viewer (not supported by tkinter backend)

[Example](cookbook/text.py)
``` python
MarkDown(md)
```

## Combobox
Editable Dropdown List

PySide6/wx/flet/tkinter share label/value resolution. text_model stores item
values for a selection; the widget displays its label. Free typing clears
index_model to -1 and preserves text through redraws, including when both models
are bound. Unbound selections follow keyed item identity. Tk uses ttk.Combobox
and native idle notification to avoid double-reporting selection text.
[Example](cookbook/combobox.py)
``` python
with ComboBox(editable=True, index_model=state("index"), text_model=state("text")):
    ComboBoxItem("Item 1")
    ComboBoxItem("Item 2")
    ComboBoxItem("Item 3")

with ComboBox(editable=False, text_model=state("text")):
    ComboBoxItem("Item 1", "Value 1")
    ComboBoxItem("Item 2", "Value 2")
    ComboBoxItem("Item 3", "Value 3")
```

wx and tkinter dialog helpers accept `dir` and the compatibility alias `directory`.
File filters accept Qt form (`"Images (*.png *.jpg);;All (*)"`) or wx form
(`"Images|*.png;*.jpg|All|*"`). `SaveFile(default=None, ...)` splits the default
path into directory and filename; an explicit directory overrides its directory.
wx cancellation returns `None`; PySide6 OpenDirectory currently returns `""`.

## TextField

wx, PySide6, flet, and tkinter finish focused edits before click callbacks.
Flet commits while retaining native focus when its public API offers no blur
method. Flet imperative window state changes are dispatched to the session loop.

Single line text editor

[Example](cookbook/textfield.py)
``` python
TextField(binding, edit_buffer_binding=None)
```

wx programmatic model updates do not emit `.input`. Enter or focus loss commits
the edit buffer once; unrelated redraws preserve an in-progress edit.

### Callbacks
* .input: edit buffer changed
* .change: editing finished


## ProgressBar
Linear progress indicator

wx and PySide6 use native integer hundredths for fractional progress/ranges.

[Example](cookbook/progressbar.py)
``` python
ProgressBar(progress, maximum=1)
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
    # Physical pixels per logical canvas pixel; 1.0 when unavailable.
    pixel_density = canvas.pixel_density
    canvas.drawText(x, y, text, w=None, h=None, size=12, color=None, rotate=0, anchor=Anchor.LEFT_TOP)
    canvas.drawLine(x1, y1, x2, y2, color=0xFF0000, width=1)
    canvas.drawPolyline([x1, y2, ..., xn, yn], color=0xFF0000, width=1)
    canvas.drawCubicBezier(start, control1, control2, end, color=0xFF0000, width=1)
    canvas.drawRect(x1, y1, x2, y2, fill=0xFF0000, stroke=0x00FF00, width=1)
    canvas.drawShapely(shape, fill=0xFF0000, stroke=0x00FF00, width=1)

Canvas(painter)
```

Canvas drawing coordinates, `canvas.width`, and `canvas.height` use logical
pixels. `canvas.pixel_density` reports the number of physical display pixels
per logical pixel and is refreshed before painting where supported. Use it to
select the resolution of raster content for HiDPI displays. Its fallback value
is `1.0`.

`drawCubicBezier()` is available on PySide6, wx, and flet. `start`, `control1`,
`control2`, and `end` are `(x, y)` coordinate pairs defining a cubic Bézier
curve.

wx ignores queued Canvas paints after native removal.

Flet canvases with `.layout(weight=1)` fill their available native drawing space.
Paint callbacks wait until both dimensions are positive and finite; the first
callback can use them for fitting a drawing. Identical resize notifications do
not repaint, while model redraws still invoke the current painter.

wx also supports `ImageResource.load(path)`, `.crop(x, y, width, height)`,
`.scale(width, height, keepAspectRatio=True, quality=0)`, `canvas.loadImage(path)`,
and `canvas.drawImage(resource, x=0, y=0, width=None, height=None, src_x=0,
src_y=0, src_width=None, src_height=None, opacity=1.0)`. Image operations return
new resources; opacity does not mutate the source. wx wheel events provide
angular deltas and modifiers; pixel deltas are zero.

### Callbacks

Flet dispatches all seven callbacks below through native GestureDetector events.
Coordinates are local logical pixels. Left and right press/drag/release sequences
continue outside the Canvas; middle-button taps use the native tertiary tap
recognizer. Hover has `button=MouseButton.NONE`; recognized drags report their
button. Callbacks and registration update on redraw, and removed canvases ignore
queued events. Drawing-only canvases do not mount a gesture wrapper.

Flet follows native gesture timing and thresholds. Double-click is primary-button
only and fires after recognition, using the second press position. A cancelled
or consumed press reports `.mouseup` with `cancelled=True` at its last reported
position; normal releases have `cancelled=False`. Applications should clear drag
state on cancellation without treating it as a completed edit. Middle-button
dragging, extra mouse buttons, and simultaneous-button tracking are unavailable.

Flet wheel `x_delta` / `y_delta` contain pixel deltas (positive left/up, matching
PySide6's sign). Angular `h_delta` / `v_delta` are `0`; no pixel-to-angle conversion
is performed. `modifiers=None` means Flet did not report modifiers. Consumers
that only read `v_delta` must add an application-level pixel-delta path to
handle Flet wheels.

* .mouseenter
* .mouseleave
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

PySide6 uses native QTabWidget placement; tkinter applies ttk tabposition style
for NORTH/SOUTH/EAST/WEST. Theme/platform appearance may differ.

wx uses a native Notebook with one content widget or layout per Tab. Keyed pages
can be reordered/removed and labels update reactively. `Tabs.NORTH/SOUTH/EAST/WEST`
select placement; changing placement remounts the native notebook. wx
`Label(..., selectable=True)` and `Text(..., selectable=True)` use read-only
TextCtrl controls. Changing selectability remounts the control.

## Stack

Stack overlays children; later declarations paint above earlier declarations.
PySide6 and Flet have native implementations. wx needs a native layout strategy.

## Image

Flet Image(path) sends file bytes, reloads when mtime changes, and uses native
aspect-preserving containment within explicit dimensions.

wx `Image(path)` uses StaticBitmap, reloads when the file modification time
changes, and scales to explicit width/height while preserving aspect ratio.
Weighted fill/stretch behavior remains pending.

[Example](cookbook/tab.py)

## Table

Table widget

wx uses wx.grid.Grid for TableNode rows and BaseTableAdapter data. Text and
numeric cells edit inline; choice and boolean cells use a native dropdown.
Raw values retain their types, duplicate choice labels are supported, and
`display` stays separate from editing data. Only bindings or `.set()` callbacks
enable declarative editing; missing cells are read-only blanks. Invalid numeric
edits do not change the model. Arbitrary objects without choices remain read-only.
Headers, native cell selection/scrolling, click/double-click callbacks, and both
`autofit` modes are supported. Redraws and removal cancel unfinished edits;
`autofit=False` retains native/user column widths. Large-data optimization and
manual keyboard/platform validation remain in [wx progress](doc/wx-progress.md).

PySide6 refreshes a reused adapter through a native model reset, including changes
to row/column counts. A reset may clear native selection or an active editor.

Flet supports TableNode rows and BaseTableAdapter using its built-in DataTable.
Editable `choices` cells use Dropdowns; other editable cells open a Save/Cancel
dialog. Supported dialog values are strings, integers, floats, booleans, and
`None` (edited as text). Raw choice values keep their types; duplicate labels are
allowed. `display` is separate from raw editing data. Choices do not make a
read-only cell editable. Editable choice cells give gestures to the Dropdown,
so cell click/double-click callbacks apply to ordinary cells. A choice cell
with an explicit display value shows it as the Dropdown label. Missing cells
are inert blanks.

Keyed TableNode rows/cells preserve drafts on reorder. Removing a cell/table,
changing its raw value, or disabling editing cancels its draft. Adapter dialogs
cancel whenever the table is reconciled because adapters have no stable row keys.
Native horizontal/vertical scrolling is provided; headers scroll with the table.
Only content-based sizing (`autofit=True`) is supported; `autofit=False` raises
`NotImplementedError`. Qt cell selection, additional typed editors, and paging
are outside this implementation. See [Flet progress](doc/flet-progress.md).

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

wx uses DataViewCtrl with TreeNode declarations or BaseTreeAdapter data.
The content column autosizes after model updates.
Keyed TreeNodes and stable adapter node objects retain selection and expansion
through redraws, reordering, relabeling, and adapter moves. TreeNode `.click` and
`.dblclick` receive the same event argument as PySide6 (None); `.expand` and
`.collapse` invoke their callbacks without an event. Adapters receive the node
object through their corresponding callbacks. `.expandAll()`, `.collapseAll()`,
and `.expandable(enabled)` work before mounting and on a live Tree. Disabling
user expansion still allows imperative expansion/collapse. Drag/drop remains
pending the shared contract.

*There should be a `TreeTable` for multi/fixed-column trees and a `NestedTable` for variable-column trees, but they have not been implemented yet*

[Example with TreeNode](cookbook/tree.py)

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

## TimelineView

`TimelineView(ttl_sec)` requests reactive redraws periodically. Timers follow
reconciled nodes, use daemon threads, and stop after removal. Backend views must
marshal their redraws to the native UI/session queue. wx, Flet, and Tkinter do
so. Tkinter queues redraws outside geometry idle flushes to prevent reconciliation
reentry. See [flet progress](doc/flet-progress.md) and
[tkinter progress](doc/tkinter-progress.md) for validation and remaining work.

## flet alignment status

The backend targets current Flet 1.x (tested with 1.0.4); install with
`pip install 'QPUIQ[flet]'`. It uses ft.run, Button(content), and
Tabs/TabBar/TabBarView. Labels use Container.on_click for ordinary text and
Text.on_tap for selectable text. Reactive FView/PUI redraws queue on the session loop and
commit one page update after reconciliation. Native Container shells apply
weights, dimensions, padding/margins, and background; text styles reset when
omitted. Window uses Page.window, with initial-only flags and imperative methods.
Tabs supports NORTH/SOUTH and preserves keyed selection. Stack is native.

Scroll uses async scroll_to; END uses Flet's native end sentinel/auto_scroll.
Current Dropdown supports ComboBox/ComboBoxItem, editable text, and distinct
item values. Image sends file bytes and reloads on mtime changes. Canvas uses
native Text/Path/Rect/Oval and supports cubic paths; image crop/resources and
text height clipping remain pending. Progress is clamped to its
range; maximum=0 uses the native indeterminate indicator. Live web-client smoke
checks cover counter updates, editor commits, Tabs, fixed-size canvas drawing,
and weighted canvas initial fit and resizing;
scroll interaction and broader visual checks remain pending. See
[flet process and progress](doc/flet-progress.md).

## tkinter alignment status

Tkinter source fixes reuse the native interpreter, coalesce subview redraws,
resolve retired controls, emit TextField event values, rebind/suppress traces,
and deduplicate commits. Checkbox/RadioButton update labels and clicks; Tabs no
longer uses Qt destruction APIs. HBox/VBox apply four-sided grid padding and
reset removed weights/styles. `Application.quit()` requests native teardown.
Twelve Tkinter native regression checks and all 17 supported cookbook pages pass
in the local env/ runtime. Redraws and quit run outside geometry idle flushes,
preventing reentrant reconciliation. Text widgets
still use their native character/line sizing units; pixel-dimension wrappers
need an agreed design. See [tkinter process and progress](doc/tkinter-progress.md).

Tkinter Canvas source now includes native polygon, rectangle, and ellipse drawing
and accepts text size/color/rotation/anchor parameters. It does not yet support
cubic paths, general image resources, or text height clipping. Scroll owns its
outer container, handles empty bounds, preserves offset requests, and filters
wheel events to its own descendants instead of changing global wheel bindings.
The Canvas cookbook example skips cubic drawing on Tkinter. Broader resize and
platform checks remain open.

## Textual alignment status

Textual alignment is planned in [Textual plan and progress](doc/textual-progress.md).
The source audit identifies lifecycle, reconciliation, input, layout, and scroll
gaps; Textual runtime validation is pending. Existing matrix entries identify
native mappings, not completed parity.

## Backend installation

Select `QPUIQ[pyside6]`, `QPUIQ[wx]`, `QPUIQ[flet]`, or `QPUIQ[textual]`.
For Tkinter, install plain `QPUIQ` with native Tk support in the selected Python.
The optional `QPUIQ[tkinter]` spelling has no additional pip dependency.
See [installation](README.md#installation).
