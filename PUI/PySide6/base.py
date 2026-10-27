from __future__ import annotations
from .. import _typing as _t
from .. import *
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QApplication

def qcolor(value):
    from ..color import rgba
    return QtGui.QColor(*rgba(value)) if type(value) is int else QtGui.QColor(value)


def qt_css_color(value):
    from ..color import rgba
    r, g, b, a = rgba(value)
    return f'#{r:02X}{g:02X}{b:02X}' if a == 255 else f'rgba({r}, {g}, {b}, {a})'


class QtViewSignal(QtCore.QObject):
    redraw = QtCore.Signal()

def _policy_priority(policy):
    policies = QtWidgets.QSizePolicy
    if policy in (policies.Expanding, policies.MinimumExpanding, policies.Ignored):
        return 4
    if policy in (policies.Preferred, policies.Minimum):
        return 1
    return 0

def _apply_params(ui, node):
    styles = {}
    if node.style_fontsize is not None:
        styles["font"] = f"{node.style_fontsize}pt"
    if node.style_fontweight is not None:
        styles["font-weight"] = str(min(900, max(100, node.style_fontweight)))
    if node.style_fontfamily is not None:
        styles["font-family"] = node.style_fontfamily
    if node.style_color is not None:
        styles["color"] = qt_css_color(node.style_color)
    if node.style_bgcolor is not None:
        styles["background-color"] = qt_css_color(node.style_bgcolor)

    style = node.qt_params.get("Style")
    if not style is None:
        ui.setStyle(style)

    HorizontalPolicy = node.qt_params.get("HorizontalPolicy")
    if not HorizontalPolicy is None:
        policy = ui.sizePolicy()
        policy.setHorizontalPolicy(HorizontalPolicy)
        ui.setSizePolicy(policy)

    VerticalPolicy = node.qt_params.get("VerticalPolicy")
    if not VerticalPolicy is None:
        policy = ui.sizePolicy()
        policy.setVerticalPolicy(VerticalPolicy)
        ui.setSizePolicy(policy)

    SizeConstraint = node.qt_params.get("SizeConstraint")
    if not SizeConstraint is None:
        ui.setSizeConstraint(SizeConstraint)

    StyleSheet = node.qt_params.get("StyleSheet", {})
    for k,v in StyleSheet.items():
        styles[k] = v

    if hasattr(ui, "setStyleSheet"):
        ui.setStyleSheet("".join([f"{k}:{v};" for k,v in styles.items()]))

    if node.layout_padding:
        ui.setContentsMargins(*trbl2ltrb(node.layout_padding))

class QtPUIView(PUIView):
    def _publish_state_ref(self, name, value):
        from . import state_ref_publish
        state_ref_publish(name, value)

    pui_virtual = True
    def __init__(self):
        super().__init__()
        self.qt_params = {}
        self._qtsignal = QtViewSignal()
        self._qtsignal.redraw.connect(self.sync, QtCore.Qt.ConnectionType.QueuedConnection) # Use QueuedConnection to prevent nested trigger

    def destroy(self, direct):
        self.destroyed = True
        if direct:
            if self.ui: # PUIView doesn't have ui
                self.ui.deleteLater()
        super().destroy(direct)

    def redraw(self):
        if self.retired_by or self.destroyed:
            return
        self.dirty = True
        if self.updating:
            return
        self.updating = True
        self._qtsignal.redraw.emit()

    def update(self, prev=None):
        super().update(prev)
        _apply_params(self.ui, self)

    def qt(self: _t.NodeT, *, Style: _t.Any = None, HorizontalPolicy: _t.Any = None,
           VerticalPolicy: _t.Any = None, SizeConstraint: _t.Any = None, StyleSheet: _t.Any = None,
           **kwargs: _t.Any) -> _t.NodeT:
        """Set Qt options; None preserves an option's previously stored value."""
        self.qt_params.update(kwargs)
        self.qt_params.update({k: v for k, v in (
            ('Style', Style), ('HorizontalPolicy', HorizontalPolicy),
            ('VerticalPolicy', VerticalPolicy), ('SizeConstraint', SizeConstraint),
            ('StyleSheet', StyleSheet),
        ) if v is not None})
        return self

class EventFilter(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.node = None

    def eventFilter(self, obj, event):
        node = self.node.get_node()
        if event.type() == QtCore.QEvent.DragEnter:
            return node.handleDragEnterEvent(event)
        elif event.type() == QtCore.QEvent.Drop:
            return node.handleDropEvent(event)
        return super().eventFilter(obj, event)

class _WindowCommands(QtCore.QObject):
    requested = QtCore.Signal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.requested.connect(self._invoke, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Slot(object)
    def _invoke(self, callback):
        callback()


class QtBaseWidget(PUINode):
    expand_x_prio = 0
    expand_y_prio = 0

    def _layout_priority(self, horizontal):
        from ..expansion import priority
        return priority(self, 'x' if horizontal else 'y')

    def _base_expansion_priority(self, axis):
        horizontal = axis == 'x'
        name = 'HorizontalPolicy' if horizontal else 'VerticalPolicy'
        policy = self.qt_params.get(name)
        if policy is not None:
            return _policy_priority(policy)
        return self.expand_x_prio if horizontal else self.expand_y_prio

    def _observe_size(self):
        from .adaptive import observe
        return observe(self)

    def get_poster(self) -> _t.Poster:
        if not hasattr(self.ui, "_pui_window_commands"):
            self.ui._pui_window_commands = _WindowCommands(self.ui)
        from ..poster import make_poster
        import math
        dispatcher = self.ui._pui_window_commands

        def later(delay, callback):
            timer = QtCore.QTimer(dispatcher)
            timer.setSingleShot(True)
            timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
            timer.timeout.connect(callback)
            timer.timeout.connect(timer.deleteLater)
            timer.start(math.ceil(delay * 1000))

        return make_poster(dispatcher.requested.emit, later)

    pui_terminal = True

    def __init__(self):
        super().__init__()
        self.qt_params = {}
        self.eventFilter = None

    def destroy(self, direct):
        self.destroyed = True
        if direct:
            if self.ui:
                try:
                    self.ui.deleteLater()
                except RuntimeError:
                    pass
        super().destroy(direct)

    def update(self, prev=None):
        super().update(prev)

        if prev and prev.eventFilter:
            self.eventFilter = prev.eventFilter
        else:
            self.eventFilter = EventFilter()
        self.eventFilter.node = self

        if not hasattr(self.ui, '_pui_native_minimum'):
            self.ui._pui_native_minimum = self.ui.minimumSize()
        native_min = self.ui._pui_native_minimum
        self.ui.setMinimumSize(max(native_min.width(), int(self._minimum_size('x') or 0)),
                               max(native_min.height(), int(self._minimum_size('y') or 0)))
        sizePolicy = self.ui.sizePolicy()
        if self.layout_width is not None:
            sizePolicy.setHorizontalPolicy(QtWidgets.QSizePolicy.Preferred)
        if self.layout_height is not None:
            sizePolicy.setVerticalPolicy(QtWidgets.QSizePolicy.Preferred)
        self.ui.setSizePolicy(sizePolicy)

        if not hasattr(self.ui, "origSizeHint"):
            self.ui.origSizeHint = self.ui.sizeHint
        self.ui.sizeHint = self.qtSizeHint

        _apply_params(self.ui, self)
        if not self._visible or (prev is not None and not prev._visible):
            self.outer.setVisible(self._visible)

    def postUpdate(self):
        if self.ui:
            if self._onDropped:
                self.ui.setAcceptDrops(True)
                self.ui.installEventFilter(self.eventFilter)
            else:
                self.ui.setAcceptDrops(False)
        super().postUpdate()

    def handleDragEnterEvent(self, event):
        from .drop import handle
        return handle(self, event, entering=True)

    def handleDropEvent(self, event):
        from .drop import handle
        return handle(self, event)

    def qtSizeHint(self):
        node = self.get_node()
        if not node.ui:
            return QtCore.QSize(0, 0)
        sh = node.ui.origSizeHint()
        w = sh.width()
        h = sh.height()
        if not node.layout_width is None:
            w = node.layout_width
        if not node.layout_height is None:
            h = node.layout_height
        return QtCore.QSize(w, h)

    def qt(self: _t.NodeT, *, Style: _t.Any = None, HorizontalPolicy: _t.Any = None,
           VerticalPolicy: _t.Any = None, SizeConstraint: _t.Any = None, StyleSheet: _t.Any = None,
           **kwargs: _t.Any) -> _t.NodeT:
        """Set Qt options; None preserves an option's previously stored value."""
        self.qt_params.update(kwargs)
        self.qt_params.update({k: v for k, v in (
            ('Style', Style), ('HorizontalPolicy', HorizontalPolicy),
            ('VerticalPolicy', VerticalPolicy), ('SizeConstraint', SizeConstraint),
            ('StyleSheet', StyleSheet),
        ) if v is not None})
        return self

    def _preClicked(self):
        focused = QApplication.focusWidget()
        if focused is not None:
            focused.clearFocus()

class QtBaseLayout(QtBaseWidget):
    pui_terminal = False
    pui_reflow_children = True
    container_x = False
    container_y = False

    def __init__(self):
        super().__init__()
        self.qt_params = {}
        if not isinstance(self.non_virtual_parent, QtBaseLayout):
            self.layout_padding = (11,11,11,11)

    @property
    def outer(self):
        return self.ui

    @property
    def inner(self):
        return self.layout

    def destroy(self, direct):
        self.layout = None
        super().destroy(direct)

    def update(self, prev=None):
        if prev and prev.ui:
            self.mounted_children = prev.mounted_children
        else:
            self.mounted_children = []

        super().update(prev)

    def addChild(self, idx, child):
        from .modal import Modal
        from .layout import Spacer
        if isinstance(child, Spacer):
            self.qtlayout.insertItem(idx, child.outer)
            self.mounted_children.insert(idx, child)
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            params = {}
            if not child.layout_weight is None:
                params["stretch"] = child.layout_weight
            self.qtlayout.insertWidget(idx, child.outer, **params)
            self.mounted_children.insert(idx, child)

    def removeChild(self, idx, child):
        from .modal import Modal
        from .layout import Spacer
        if isinstance(child, Spacer):
            self.qtlayout.removeItem(child.outer)
            self.mounted_children.pop(idx)
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
            self.mounted_children.pop(idx)

    def postUpdate(self):
        if self.ui:
            if self._onDropped:
                self.ui.setAcceptDrops(True)
                self.ui.installEventFilter(self.eventFilter)
            else:
                self.ui.setAcceptDrops(False)

        super().postUpdate()

        self.applyChildren()

    def postSync(self):
        self.applyChildren()
        super().postSync()

    def applyChildren(self):
        if not (self.container_x or self.container_y):
            return
        from .layout import Spacer
        horizontal = self.container_x
        flags, policies = QtCore.Qt.AlignmentFlag, QtWidgets.QSizePolicy
        leading = flags.AlignLeft if horizontal else flags.AlignTop
        cross_alignment = flags.AlignVCenter if horizontal else flags.AlignLeft
        children = [child.get_node() for child in self.mounted_children]
        self.mounted_children[:] = children
        priorities = [
            (5 if child.layout_weight > 0 else 0) if child.layout_weight is not None
            else child._layout_priority(horizontal)
            for child in children
        ]
        highest = max((priority for child, priority in zip(children, priorities)
                       if child._visible), default=0)
        # With no expanding children Qt otherwise distributes leftover space
        # among Preferred controls (or between Fixed ones). Pack at the start.
        self.qtlayout.setAlignment(flags(0) if highest else leading)
        for i, (child, priority) in enumerate(zip(children, priorities)):
            expands = child._visible and highest > 0 and priority == highest
            self.qtlayout.setStretch(i, int(child.layout_weight or 1) if expands else 0)
            item = self.qtlayout.itemAt(i)
            if isinstance(child, Spacer):
                main = policies.Expanding if expands else policies.Fixed
                child.ui.changeSize(0, 0, main if horizontal else policies.Minimum,
                                    policies.Minimum if horizontal else main)
                continue
            cross_expands = child._layout_priority(not horizontal) > 0
            item.setAlignment((flags(0) if expands else leading) |
                              (flags(0) if cross_expands else cross_alignment))
            # Explicit weight can expand even a native Fixed-height control.
            # Reset both axes each pass so direction/weight changes don't leak.
            policy = child.outer.sizePolicy()
            for x_axis, grow in ((horizontal, expands), (not horizontal, cross_expands)):
                name = 'HorizontalPolicy' if x_axis else 'VerticalPolicy'
                value = child.qt_params.get(name)
                if value is None:
                    value = policies.Expanding if grow else policies.Preferred
                if x_axis:
                    policy.setHorizontalPolicy(value)
                else:
                    policy.setVerticalPolicy(value)
            child.outer.setSizePolicy(policy)
        self.qtlayout.invalidate()

class QtBaseFrame(QtBaseWidget):
    pui_terminal = False

    def destroy(self, direct):
        self.destroyed = True
        if direct:
            if self.ui:
                self.ui.deleteLater()
        super().destroy(direct)

    def addChild(self, idx, child):
        if idx != 0:
            return
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            self.ui.setWidget(child.outer)
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if idx != 0:
            return
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
        elif child.children:
            self.removeChild(idx, child.children[0])

class QtInPui(QtBaseWidget):
    def __init__(self, widget, *args):
        self._internal_tag = str(id(widget))
        super().__init__(*args)
        self.ui = widget

    def update(self, prev=None):
        self._native_policy = (prev._native_policy if prev is not None else
                               self.ui.sizePolicy())
        super().update(prev)

    def _base_expansion_priority(self, axis):
        horizontal = axis == 'x'
        name = 'HorizontalPolicy' if horizontal else 'VerticalPolicy'
        if name in self.qt_params:
            return super()._base_expansion_priority(axis)
        return _policy_priority(self._native_policy.horizontalPolicy() if horizontal
                                else self._native_policy.verticalPolicy())

    def destroy(self, direct):
        PUINode.destroy(self, direct)

class PuiInQt(QtPUIView):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.ui.update()

    def addChild(self, idx, child):
        self.ui.addChild(idx, child)

    def removeChild(self, idx, child):
        self.ui.removeChild(idx, child)


class QtWindowState:
    """Constructor-equivalent setters for the initial native window state."""
    def maximize(self, enabled=True):
        self._initial_maximize = enabled
        return self

    def fullscreen(self, enabled=True):
        self._initial_fullscreen = enabled
        return self

    def _apply_initial_window_state(self):
        state = self.ui.windowState()
        for enabled, flag in (
            (self._initial_maximize, QtCore.Qt.WindowState.WindowMaximized),
            (self._initial_fullscreen, QtCore.Qt.WindowState.WindowFullScreen),
        ):
            if enabled is not None:
                state = state | flag if enabled else state & ~flag
        self.ui.setWindowState(state)
