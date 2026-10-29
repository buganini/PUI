"""Single-column tree identity and events shared by native and browser renderers."""
from dataclasses import dataclass, field
from .node import PUINode
from .state import BaseBinding


@dataclass
class Entry:
    source: object
    parent: int
    text: str
    children: list = field(default_factory=list)


class TreeState:
    def __init__(self):
        self.entries = {0: Entry(None, 0, '')}
        self.model = None
        self.next_id = 1
        self.expanded = set()
        self.selected = None
        self.expandable = True

    def snapshot(self, tree):
        old = {id(e.source): key for key, e in self.entries.items() if key and tree.model is self.model}
        entries = {0: Entry(None, 0, '')}
        seen = set()
        def visit(source, parent):
            if id(source) in seen:
                raise ValueError('Tree nodes must have unique object identities; cycles are not allowed')
            seen.add(id(source))
            if tree.model is None:
                if not isinstance(source, TreeNode):
                    raise TypeError('Tree children must be TreeNode declarations')
                key = source._tree_id
                data, children = source.data, source.children
            else:
                key = old.get(id(source))
                data = tree.model.data(source)
                children = (tree.model.child(source, i) for i in range(tree.model.rowCount(source)))
            if key is None:
                key = self.next_id
                self.next_id += 1
            if tree.model is None:
                source._tree_id = key
            if isinstance(data, BaseBinding):
                data = data.value
            entries[key] = Entry(source, parent, '' if data is None else str(data))
            entries[parent].children.append(key)
            for child in children:
                visit(child, key)
        sources = tree.children if tree.model is None else (
            tree.model.child(None, i) for i in range(tree.model.rowCount(None)))
        for source in sources:
            visit(source, 0)
        self.entries, self.model = entries, tree.model
        self.expanded.intersection_update(k for k, e in entries.items() if k and e.children)
        if self.selected not in entries:
            self.selected = None

    def visible(self):
        result = []
        def visit(key, depth):
            result.append((key, depth))
            if key in self.expanded:
                for child in self.entries[key].children:
                    visit(child, depth + 1)
        for key in self.entries[0].children:
            visit(key, 0)
        return result


class TreeNode(PUINode):
    def __init__(self, data=''):
        super().__init__()
        self.data = data
        self._tree_id = None
        self._expand_callback = self._collapse_callback = None

    def update(self, prev):
        if prev:
            self._tree_id = prev._tree_id
        super().update(prev)

    def expand(self, callback, *args, **kwargs):
        self._expand_callback = callback, args, kwargs
        return self

    def collapse(self, callback, *args, **kwargs):
        self._collapse_callback = callback, args, kwargs
        return self

    def releaseRetiredRefs(self):
        self._expand_callback = self._collapse_callback = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        self._expand_callback = self._collapse_callback = None
        super().destroy(direct)


class TreeData:
    pui_terminal = False
    expand_x_prio = expand_y_prio = 4

    def __init__(self, model=None):
        super().__init__()
        self.model = model
        self.layout_weight = 1
        self.tree_state = TreeState()
        self._tree_pending = []

    def update(self, prev):
        if prev is not None:
            self.tree_state = prev.tree_state
        super().update(prev)

    def addChild(self, idx, child):
        pass  # TreeNode declarations are data, not standalone native controls.

    def removeChild(self, idx, child):
        pass

    def postSync(self):
        self.tree_state.snapshot(self)
        for action, value in self._tree_pending:
            self._tree_action(action, value)
        self._tree_pending.clear()
        self._render_tree()
        super().postSync()

    def _tree_action(self, action, value):
        state = self.tree_state
        if action == 'expandable':
            state.expandable = bool(value)
        else:
            state.expanded = {k for k, e in state.entries.items() if k and e.children} if value else set()

    def _request_tree(self, action, value):
        node = self.get_node()
        if node.destroyed:
            return self
        if node.ui is None:
            node._tree_pending.append((action, value))
        else:
            node._tree_action(action, value)
            node._render_tree()
        return self

    def expandAll(self):
        return self._request_tree('all', True)

    def collapseAll(self):
        return self._request_tree('all', False)

    def expandable(self, enabled):
        return self._request_tree('expandable', enabled)

    def tree_event(self, key, action):
        node = self.get_node()
        if node.destroyed or key not in node.tree_state.entries or not key:
            return False
        state, entry = node.tree_state, node.tree_state.entries[key]
        if action in ('expanded', 'collapsed'):
            if not state.expandable or not entry.children:
                return False
            if (key in state.expanded) == (action == 'expanded'):
                return False
            (state.expanded.add if action == 'expanded' else state.expanded.discard)(key)
        elif action in ('clicked', 'dblclicked', 'selected'):
            state.selected = key
        else:
            return False
        node._render_tree()
        if action == 'selected':
            return True
        if action == 'clicked':
            node._preClicked()
        if node.model is not None:
            node._invoke_callback(getattr(node.model, action), entry.source)
        else:
            attribute = {'clicked': '_onClicked', 'dblclicked': '_onDblClicked',
                         'expanded': '_expand_callback', 'collapsed': '_collapse_callback'}[action]
            callback = getattr(entry.source, attribute)
            if callback:
                cb, args, kwargs = callback
                node._invoke_callback(cb, *((None,) if action in ('clicked', 'dblclicked') else ()), *args, **kwargs)
        return True
