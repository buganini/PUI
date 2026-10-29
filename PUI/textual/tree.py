"""Single-column trees rendered by Textual's native Tree widget."""
from rich.text import Text
from textual.widgets import Tree as NativeTree
from .base import TBase
from .._tree import TreeData, TreeNode


class _Tree(NativeTree):
    _click_chain = 0

    def on_click(self, event):
        self._click_chain = event.chain

    def on_key(self, event):
        self._click_chain = 0

    def _current(self, event):
        event.stop()
        node = self.puinode.get_node()
        if node.destroyed or node._items.get(event.node.data) is not event.node:
            return None
        return node

    def on_tree_node_selected(self, event):
        node = self._current(event)
        chain, self._click_chain = self._click_chain, 0
        if node:
            self._dispatch(node, event.node.data, 'dblclicked' if chain == 2 else 'clicked')
            if chain == 2 and not node.get_node().destroyed:
                self._toggle_node(event.node)

    def on_tree_node_highlighted(self, event):
        node = self._current(event)
        if node:
            node.tree_state.selected = event.node.data

    def _dispatch(self, node, key, action):
        # Native changes precede queued messages. Re-rendering the whole tree
        # here would undo other changes whose messages have not arrived yet.
        node._reflecting_native = True
        try:
            node.tree_event(key, action)
        finally:
            node._reflecting_native = False
        if action in ('expanded', 'collapsed') and not node.tree_state.expandable:
            node._render_tree()

    def on_tree_node_expanded(self, event):
        node = self._current(event)
        if node:
            self._dispatch(node, event.node.data, 'expanded')

    def on_tree_node_collapsed(self, event):
        node = self._current(event)
        if node:
            self._dispatch(node, event.node.data, 'collapsed')


class Tree(TreeData, TBase):
    _reflecting_native = False

    def update(self, prev):
        if prev is not None:
            self.ui, self._items, self._structure = prev.ui, prev._items, prev._structure
        else:
            self.ui = _Tree('')
            self.ui.show_root = False
            self.ui.auto_expand = False
            self._items, self._structure = {}, None
        self.ui.puinode = self
        super().update(prev)

    def _render_tree(self):
        if self._reflecting_native:
            return
        state, ui = self.tree_state, self.ui
        structure = tuple((key, entry.parent, tuple(entry.children)) for key, entry in state.entries.items())
        rebuild = structure != self._structure
        messages = (NativeTree.NodeSelected, NativeTree.NodeHighlighted,
                    NativeTree.NodeExpanded, NativeTree.NodeCollapsed)
        with ui.prevent(*messages):
            if rebuild:
                # Textual has no public reparent/reorder API. Rebuild native nodes
                # only for structural changes, retaining logical identity in TreeState.
                ui.root.remove_children()
                self._items = {0: ui.root}
                for key, entry in state.entries.items():
                    if key:
                        self._items[key] = self._items[entry.parent].add(Text(entry.text), data=key)
                self._structure = structure
            if not ui.root.is_expanded:
                ui.root.expand()
            for key, item in self._items.items():
                if not key:
                    continue
                entry = state.entries[key]
                if item.label.plain != entry.text:
                    item.set_label(Text(entry.text))
                item.allow_expand = bool(entry.children) and state.expandable
                if item.is_expanded != (key in state.expanded):
                    (item.expand if key in state.expanded else item.collapse)()
        if rebuild:
            ui.call_after_refresh(self._restore_cursor)

    def _restore_cursor(self):
        node = self.get_node()
        if node.destroyed:
            return
        key = node.tree_state.selected
        visible = {k for k, _ in node.tree_state.visible()}
        while key and key not in visible:
            key = node.tree_state.entries[key].parent
        if key:
            with node.ui.prevent(NativeTree.NodeHighlighted, NativeTree.NodeSelected):
                node.ui.move_cursor(node._items[key])

    def _request_tree(self, action, value):
        node = self.get_node()
        if node.ui is None or node.destroyed:
            return super()._request_tree(action, value)
        app = node.root._textual_app()
        def apply():
            current = node.get_node()
            if not current.destroyed:
                current._tree_action(action, value)
                current._render_tree()
        app._pui_loop.call_soon_threadsafe(apply)
        return self
