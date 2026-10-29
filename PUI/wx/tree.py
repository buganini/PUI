from .base import *
import wx.dataview as dv
from dataclasses import dataclass, field


def _item_id(item):
    return int(item.GetID()) if item.IsOk() else 0


@dataclass
class _Entry:
    source: object
    parent: int
    text: str
    children: list = field(default_factory=list)


class _TreeModel(dv.DataViewModel):
    def __init__(self):
        super().__init__()
        self.entries = {0: _Entry(None, 0, '')}
        self.next_id = 1
        self.node = None
        self.syncing = False

    def allocate(self):
        identity = self.next_id
        self.next_id += 1
        return identity

    def GetColumnCount(self):
        return 1

    def GetColumnType(self, column):
        return 'string'

    def GetValue(self, item, column):
        entry = self.entries.get(_item_id(item))
        return entry.text if entry else ''

    def SetValue(self, value, item, column):
        return False

    def GetParent(self, item):
        entry = self.entries.get(_item_id(item))
        return dv.DataViewItem(entry.parent if entry else 0)

    def IsContainer(self, item):
        entry = self.entries.get(_item_id(item))
        return not item.IsOk() or bool(entry and entry.children)

    def GetChildren(self, item, children):
        entry = self.entries.get(_item_id(item))
        ids = entry.children if entry else []
        for identity in ids:
            children.append(dv.DataViewItem(identity))
        return len(ids)

    def HasDefaultCompare(self):
        return True

    def Compare(self, first, second, column, ascending):
        a, b = _item_id(first), _item_id(second)
        if a not in self.entries or b not in self.entries:
            return 0
        parent = self.entries[a].parent
        if parent != self.entries[b].parent:
            return 0
        siblings = self.entries[parent].children
        difference = siblings.index(a) - siblings.index(b)
        return difference if ascending else -difference

    def snapshot(self, node):
        result = {0: _Entry(None, 0, '')}
        # Keep references to old adapter objects until the snapshot is built, so
        # Python object IDs cannot be recycled for newly inserted nodes.
        adapter_ids = {id(entry.source): identity for identity, entry in self.entries.items()
                       if identity and node.model is self.node.model}

        def visit(source, parent):
            if node.model is None:
                if not isinstance(source, TreeNode):
                    return
                if source._item_id is None:
                    source._item_id = self.allocate()
                identity = source._item_id
                value = source.data
                if isinstance(value, BaseBinding):
                    value = value.value
                children = source.children
            else:
                identity = adapter_ids.get(id(source))
                if identity is None:
                    identity = self.allocate()
                value = node.model.data(source)
                children = (node.model.child(source, i) for i in range(node.model.rowCount(source)))
            if identity in result:
                raise ValueError('Tree adapter nodes must have unique object identities')
            result[identity] = _Entry(source, parent, str(value))
            result[parent].children.append(identity)
            for child in children:
                visit(child, identity)

        sources = node.children if node.model is None else (
            node.model.child(None, i) for i in range(node.model.rowCount(None)))
        for source in sources:
            visit(source, 0)
        return result

    def refresh(self, node):
        upcoming = self.snapshot(node)
        ui = node.ui
        expanded = {identity for identity in self.entries if identity
                    and ui.IsExpanded(dv.DataViewItem(identity))}
        selected = _item_id(ui.GetSelection())
        previous = self.entries
        structure_changed = previous.keys() != upcoming.keys() or any(
            entry.parent != upcoming[identity].parent
            or bool(entry.children) != bool(upcoming[identity].children)
            for identity, entry in previous.items() if identity in upcoming)
        self.syncing = True
        try:
            self.entries = upcoming
            self.node = node
            if structure_changed:
                # Let the native model rebuild its hierarchy together, including
                # leaf/container transitions. Reapply retained view state below.
                self.Cleared()
            else:
                for identity, entry in upcoming.items():
                    if identity and previous[identity].text != entry.text:
                        self.ItemChanged(dv.DataViewItem(identity))
                self.Resort()
            # Iteration is parent-first; restoration does not emit user callbacks.
            for identity in upcoming:
                if identity in expanded:
                    ui.Expand(dv.DataViewItem(identity))
            if selected in upcoming and selected:
                ui.Select(dv.DataViewItem(selected))
            node._queue_column_fit()
        finally:
            self.syncing = False


class Tree(WxBaseWidget):
    pui_terminal = False
    expand_x_prio = expand_y_prio = 4

    def __init__(self, model=None):
        super().__init__()
        self.model = model
        self.layout_weight = 1
        self.pendings = []
        self._expandable = True
        self._programmatic = False

    def update(self, prev):
        if prev and prev.ui:
            self.ui, self.wx_model = prev.ui, prev.wx_model
            self._expandable = prev._expandable
        else:
            self.ui = dv.DataViewCtrl(getWindow(self.parent), style=dv.DV_NO_HEADER)
            self.wx_model = _TreeModel()
            self.wx_model.node = self
            self.ui.AssociateModel(self.wx_model)
            self.wx_model.DecRef()
            self.ui.AppendTextColumn('', 0, width=wx.COL_WIDTH_AUTOSIZE)
            self.ui.Bind(wx.EVT_SIZE, self._size_changed)
            self.ui.Bind(wx.EVT_LEFT_UP, lambda event: self.ui_event(event, 'clicked'))
            self.ui.Bind(wx.EVT_LEFT_DCLICK, lambda event: self.ui_event(event, 'dblclicked'))
            self.ui.Bind(dv.EVT_DATAVIEW_ITEM_EXPANDING, self.expansion_request)
            self.ui.Bind(dv.EVT_DATAVIEW_ITEM_COLLAPSING, self.expansion_request)
            self.ui.Bind(dv.EVT_DATAVIEW_ITEM_EXPANDED, lambda event: self.item_event(event, 'expanded'))
            self.ui.Bind(dv.EVT_DATAVIEW_ITEM_COLLAPSED, lambda event: self.item_event(event, 'collapsed'))
        super().update(prev)

    def _size_changed(self, event):
        event.Skip()
        self.get_node()._queue_column_fit(measure=False)

    def _queue_column_fit(self, measure=True):
        node = self.get_node()
        if node.destroyed or not node.ui:
            return
        ui = node.ui
        ui._pui_measure_column = getattr(ui, '_pui_measure_column', False) or measure
        if getattr(ui, '_pui_column_fit_pending', False):
            return
        ui._pui_column_fit_pending = True
        def fit():
            current = node.get_node()
            if current.destroyed or not ui or ui.IsBeingDeleted():
                return
            # Let native layout/expansion settle before measuring. Recompute the
            # content width so shrinking a window or shortening labels can shrink
            # the column again, but never leave unused space in this single column.
            column = ui.GetColumn(0)
            if ui._pui_measure_column or not hasattr(ui, '_pui_content_width'):
                ui._pui_measure_column = False
                column.SetWidth(wx.COL_WIDTH_AUTOSIZE)
                ui._pui_content_width = column.GetWidth()
            width = max(ui._pui_content_width, ui.GetClientSize().width)
            if column.GetWidth() != width:
                column.SetWidth(width)
            ui._pui_column_fit_pending = False
        wx.CallAfter(fit)

    def postSync(self):
        self.wx_model.refresh(self)
        for method, args in self.pendings:
            getattr(self, method)(*args)
        self.pendings.clear()
        super().postSync()

    def dispatch(self, item, action):
        node = self.get_node()
        if node.destroyed or node.wx_model.syncing:
            return
        entry = node.wx_model.entries.get(_item_id(item))
        if entry is None or not item.IsOk():
            return
        if action == 'clicked':
            node._preClicked()
        if node.model is not None:
            getattr(node.model, action)(entry.source)
        elif not entry.source.destroyed:
            if action in ('clicked', 'dblclicked'):
                getattr(entry.source, '_' + action)(None)
            else:
                entry.source.notify(action)

    def ui_event(self, event, action):
        node = self.get_node()
        if not node.destroyed and node.ui:
            item, column = node.ui.HitTest(event.GetPosition())
            if item.IsOk() and node.ui.GetItemRect(item).Contains(event.GetPosition()):
                if action == 'clicked' and getattr(node.ui, '_pui_skip_release', False):
                    node.ui._pui_skip_release = False
                elif action == 'dblclicked':
                    node.ui._pui_skip_release = True
                    node.ui.Select(item)
                    if node._expandable and node.wx_model.IsContainer(item):
                        (node.ui.Collapse if node.ui.IsExpanded(item) else node.ui.Expand)(item)
                    node.dispatch(item, action)
                    return  # Do not also run platform-specific double-click activation.
                else:
                    node.dispatch(item, action)
        event.Skip()

    def item_event(self, event, action):
        self.get_node().dispatch(event.GetItem(), action)
        self.get_node()._queue_column_fit()
        event.Skip()

    def expansion_request(self, event):
        node = self.get_node()
        if not node.destroyed and (node._expandable or node._programmatic or node.wx_model.syncing):
            event.Skip()
        else:
            event.Veto()

    def _all(self, expand):
        node = self.get_node()
        if node.destroyed:
            return self
        if node.ui is None:
            node.pendings.append(('expandAll' if expand else 'collapseAll', ()))
        else:
            node._programmatic = True
            try:
                identities = list(node.wx_model.entries)
                for identity in identities if expand else reversed(identities):
                    if identity and node.wx_model.entries[identity].children:
                        (node.ui.Expand if expand else node.ui.Collapse)(dv.DataViewItem(identity))
            finally:
                node._programmatic = False
        return self

    def expandAll(self):
        return self._all(True)

    def collapseAll(self):
        return self._all(False)

    def expandable(self, enabled):
        node = self.get_node()
        if not node.destroyed:
            if node.ui is None:
                node.pendings.append(('expandable', (enabled,)))
            else:
                node._expandable = bool(enabled)
        return self

    def destroy(self, direct):
        self.wx_model.syncing = True
        self.wx_model.node = None
        self.wx_model.entries = {0: _Entry(None, 0, '')}
        self.wx_model.Cleared()
        self.pendings.clear()
        super().destroy(direct)


class TreeNode(PUINode):
    def __init__(self, data=''):
        super().__init__()
        self.data = data
        self._item_id = None
        self._expand_callback = self._collapse_callback = None

    def update(self, prev):
        if prev:
            self._item_id = prev._item_id
        super().update(prev)

    def expand(self, callback, *args, **kwargs):
        self._expand_callback = callback, args, kwargs
        return self

    def collapse(self, callback, *args, **kwargs):
        self._collapse_callback = callback, args, kwargs
        return self

    def notify(self, action):
        callback = self._expand_callback if action == 'expanded' else self._collapse_callback
        if callback:
            cb, args, kwargs = callback
            cb(*args, **kwargs)

    def releaseRetiredRefs(self):
        self._expand_callback = self._collapse_callback = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        self._expand_callback = self._collapse_callback = None
        super().destroy(direct)
