from __future__ import annotations
from .. import _typing as _t
from collections.abc import Mapping, Sequence

from .. import *
from .._table import decorate, decorations, placeholder
from .base import *

class QtTableModelAdapter(QtCore.QAbstractTableModel):
    def __init__(self, pui_node: "Table"):
        super().__init__()
        self.pui_node = pui_node
        self.model = pui_node.model

    def refresh(self):
        # An adapter may have changed both values and dimensions in place.
        self.beginResetModel()
        self.endResetModel()

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            return self.model.data(index.row(), index.column())
        elif role == QtCore.Qt.EditRole:
            return self.model.editData(index.row(), index.column())

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            self.model.setData(index.row(), index.column(), value)
            return True

    def flags(self, index):
        flags = super().flags(index)
        if self.model.editable(index.row(), index.column()):
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                if hasattr(self.model, "columnHeader"):
                    if self.model.columnHeader is None:
                        if self.pui_node.columnHeader:
                            return self.pui_node.columnHeader[section]
                        else:
                            return None
                    else:
                        return self.model.columnHeader(section)
                else:
                    return super().headerData(section, orientation, role)
            else:
                if hasattr(self.model, "rowHeader"):
                    if self.model.rowHeader is None:
                        if self.pui_node.rowHeader:
                            return self.pui_node.rowHeader[section]
                        else:
                            return None
                    else:
                        return self.model.rowHeader(section)
                else:
                    return super().headerData(section, orientation, role)

    def rowCount(self, index):
        return self.model.rowCount()

    def columnCount(self, index):
        return self.model.columnCount()

    def clicked(self, index):
        self.model.clicked(index.row(), index.column())

    def dblclicked(self, index):
        self.model.dblclicked(index.row(), index.column())


class QtTableNodeModelAdapter(QtCore.QAbstractTableModel):
    def __init__(self, pui_node):
        super().__init__()
        self.pui_node = pui_node
        self.children = pui_node.children

    def nodeAt(self, row, column):
        if row < 0 or row >= len(self.children):
            return None
        children = self.children[row].children
        if column < 0 or column >= len(children):
            return None
        return children[column]

    def data(self, index, role):
        node = self.nodeAt(index.row(), index.column())
        if node is None:
            return None
        if role == QtCore.Qt.DisplayRole:
            if node.display is not None:
                value = self.resolve(node.display)
            else:
                value = self.resolve(node.data)
                if isinstance(node.choices, Mapping):
                    try:
                        if value in node.choices:
                            value = self.resolve(node.choices[value])
                    except TypeError:
                        pass
                elif isinstance(node.data, BaseBinding):
                    value = str(value)
            return decorate(node, value) if any(decorations(node)) else value
        if role == QtCore.Qt.EditRole:
            return self.resolve(node.data)
        return None

    @staticmethod
    def resolve(data):
        return data.value if isinstance(data, BaseBinding) else data

    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            node = self.nodeAt(index.row(), index.column())
            if node is None:
                return False
            if isinstance(node.data, BaseBinding):
                node.data.value = value
            else:
                node._set(value)
            return True
        return False

    def flags(self, index):
        node = self.nodeAt(index.row(), index.column())
        if node is None:
            return QtCore.Qt.ItemFlag.NoItemFlags
        flags = super().flags(index)
        if isinstance(node.data, BaseBinding) or node._set_callback:
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                headers = self.pui_node.columnHeader
            else:
                headers = self.pui_node.rowHeader
            if headers is not None:
                if 0 <= section < len(headers):
                    return headers[section]
                return None
        return super().headerData(section, orientation, role)

    def rowCount(self, index):
        if self.pui_node.rowCount is not None:
            return self.pui_node.rowCount
        counts = [len(self.children)]
        if self.pui_node.rowHeader is not None:
            counts.append(len(self.pui_node.rowHeader))
        return max(counts)

    def columnCount(self, index):
        if self.pui_node.columnCount is not None:
            return self.pui_node.columnCount
        counts = [len(row.children) for row in self.children]
        if self.pui_node.columnHeader is not None:
            counts.append(len(self.pui_node.columnHeader))
        return max(counts, default=0)

    def clicked(self, index):
        node = self.nodeAt(index.row(), index.column())
        if node is not None:
            node._clicked(None)

    def dblclicked(self, index):
        node = self.nodeAt(index.row(), index.column())
        if node is not None:
            node._dblclicked(None)


class QtTableNodeDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, table, parent=None):
        super().__init__(parent)
        self.table = table
        self.closeEditor.connect(self._closing_editor)

    def _closing_editor(self, editor, hint=None):
        if isinstance(editor, _DecoratedEditor):
            editor.closing = True
            editor.field.removeEventFilter(self)
            editor.removeEventFilter(self)

    def destroyEditor(self, editor, index):
        self._closing_editor(editor)
        super().destroyEditor(editor, index)

    def nodeAt(self, index):
        return self.table.qt_model.nodeAt(index.row(), index.column())

    def createEditor(self, parent, option, index):
        node = self.nodeAt(index)
        if node is None:
            return super().createEditor(parent, option, index)
        if node.choices is None:
            field = super().createEditor(parent, option, index)
        else:
            field = QtWidgets.QComboBox(parent)
            field.setBackgroundRole(QtGui.QPalette.ColorRole.Base)
            field.setAutoFillBackground(True)
            for value, display in node.choiceItems():
                field.addItem(
                    str(QtTableNodeModelAdapter.resolve(display)),
                    QtTableNodeModelAdapter.resolve(value),
                )
            field.activated.connect(self.commitChoice)
        hint = placeholder(node)
        if isinstance(field, (QtWidgets.QLineEdit, QtWidgets.QComboBox)):
            field.setPlaceholderText(hint)
        parts = decorations(node)
        if not any(parts):
            return field
        editor = _DecoratedEditor(field, parts, parent)
        return editor

    def commitChoice(self, _index):
        editor = self.sender()
        if isinstance(editor, QtWidgets.QComboBox):
            editor = editor.parentWidget() if isinstance(editor.parentWidget(), _DecoratedEditor) else editor
            self.commitData.emit(editor)
            self.closeEditor.emit(editor)

    @staticmethod
    def field(editor):
        return editor.field if isinstance(editor, _DecoratedEditor) else editor

    def eventFilter(self, editor, event):
        wrapper = editor.parentWidget() if isinstance(editor.parentWidget(), _DecoratedEditor) else editor
        if isinstance(wrapper, _DecoratedEditor):
            if wrapper.closing:
                return False
            if (editor is not wrapper and event.type() == QtCore.QEvent.Type.KeyPress
                    and event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter)):
                if isinstance(editor, (QtWidgets.QLineEdit, QtWidgets.QAbstractSpinBox)):
                    if not editor.hasAcceptableInput():
                        return True
                    if isinstance(editor, QtWidgets.QAbstractSpinBox):
                        editor.interpretText()
                self.commitData.emit(wrapper)
                self.closeEditor.emit(wrapper, self.EndEditHint.SubmitModelCache)
                return True
            # Key events ignored by the field propagate to its parent. Handle
            # them once, on the field, rather than queueing two commits.
            if editor is wrapper and event.type() in (QtCore.QEvent.Type.KeyPress,
                                                       QtCore.QEvent.Type.ShortcutOverride):
                return False
        return super().eventFilter(wrapper, event)

    def setEditorData(self, editor, index):
        if isinstance(editor, _DecoratedEditor):
            editor.field.installEventFilter(self)
        editor = self.field(editor)
        if not isinstance(editor, QtWidgets.QComboBox):
            super().setEditorData(editor, index)
            return
        value = index.model().data(index, QtCore.Qt.EditRole)
        for choice_index in range(editor.count()):
            if editor.itemData(choice_index) == value:
                editor.setCurrentIndex(choice_index)
                return
        editor.setCurrentIndex(-1)
        editor.setPlaceholderText(placeholder(self.nodeAt(index)) or str(value))

    def setModelData(self, editor, model, index):
        editor = self.field(editor)
        if not isinstance(editor, QtWidgets.QComboBox):
            super().setModelData(editor, model, index)
            return
        if editor.currentIndex() >= 0:
            model.setData(index, editor.currentData(), QtCore.Qt.EditRole)


class _DecoratedEditor(QtWidgets.QWidget):
    def __init__(self, field, parts, parent=None):
        super().__init__(parent)
        self.setBackgroundRole(QtGui.QPalette.ColorRole.Base)
        self.setAutoFillBackground(True)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        if parts[0]:
            layout.addWidget(QtWidgets.QLabel(parts[0], self))
        layout.addWidget(field, 1)
        if parts[1]:
            layout.addWidget(QtWidgets.QLabel(parts[1], self))
        self.closing = False
        self._field_index = 1 if parts[0] else 0
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.field.setFocus(event.reason())

    @property
    def field(self):
        # Qt owns the factory-created editor after createEditor returns; retrieve
        # its current Python wrapper instead of retaining the invalidated one.
        return self.layout().itemAt(self._field_index).widget()

class Table(QtBaseWidget):
    expand_x_prio = expand_y_prio = 4
    def __init__(
        self,
        model: _t.Any = None,
        autofit: bool = True,
        columnHeader: _t.Sequence[_t.Any] | None = None,
        rowHeader: _t.Sequence[_t.Any] | None = None,
        columnCount: int | None = None,
        rowCount: int | None = None,
    ) -> None:
        super().__init__()
        for name, count in (("columnCount", columnCount), ("rowCount", rowCount)):
            if count is not None and (
                not isinstance(count, int) or isinstance(count, bool) or count < 0
            ):
                raise ValueError(f"{name} must be a non-negative integer or None")
        self.layout_weight = 1
        self.model = model
        self.autofit = autofit
        self.curr_model = None
        self.columnHeader = columnHeader
        self.rowHeader = rowHeader
        self.columnCount = columnCount
        self.rowCount = rowCount

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.qt_model = prev.qt_model
            self.curr_model = prev.curr_model

            self.ui.clicked.disconnect()
            self.ui.doubleClicked.disconnect()
        else:
            self.qt_model = None
            self.curr_model = Prop()
            self.ui = QtWidgets.QTableView()

        self.ui.clicked.connect(self.on_item_clicked)
        self.ui.doubleClicked.connect(self.on_item_double_clicked)

        if self.model:
            if self.curr_model.set(self.model):
                self.qt_model = QtTableModelAdapter(self)
                self.ui.setModel(self.qt_model)
            else:
                self.qt_model.pui_node = self
                self.qt_model.refresh()
        else:
            self.ui.horizontalHeader().hide()
            self.ui.verticalHeader().hide()
            self.qt_model = QtTableNodeModelAdapter(self)
            self.ui.setModel(self.qt_model)
            self.delegate = QtTableNodeDelegate(self, self.ui)
            self.ui.setItemDelegate(self.delegate)

        if (self.model is None or self.model.columnHeader is None) and self.columnHeader is None:
            self.ui.horizontalHeader().hide()
        else:
            self.ui.horizontalHeader().show()

        if (self.model is None or self.model.rowHeader is None) and self.rowHeader is None:
            self.ui.verticalHeader().hide()
        else:
            self.ui.verticalHeader().show()

        if self.autofit:
            self.ui.resizeColumnsToContents()

        super().update(prev)

    def on_item_clicked(self, index):
        self.get_node().qt_model.clicked(index)

    def on_item_double_clicked(self, index):
        self.get_node().qt_model.dblclicked(index)


class TableNode(PUINode):
    def __init__(
        self,
        data: _t.Any = "",
        *,
        display: _t.Any = None,
        choices: _t.Choices | None = None,
        prefix: _t.Any = '',
        suffix: _t.Any = '',
        placeholder: _t.Any = None,
    ) -> None:
        super().__init__()
        if choices is not None and (
            isinstance(choices, (str, bytes))
            or not isinstance(choices, (Mapping, Sequence))
        ):
            raise TypeError("choices must be a mapping, sequence, or None")
        self._set_callback = None
        self.data = data
        self.display = display
        self.choices = choices
        self.prefix, self.suffix = prefix, suffix
        self.placeholder = placeholder

    def choiceItems(self):
        if isinstance(self.choices, Mapping):
            return self.choices.items()
        return ((value, value) for value in self.choices)

    def set(self, cb, *args, **kwargs):
        self._set_callback = (cb, args, kwargs)
        return self

    def _set(self, data):
        if self._set_callback:
            cb, args, kwargs = self._set_callback
            cb(data, *args, **kwargs)
