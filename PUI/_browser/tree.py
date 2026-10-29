"""Shared Web/Pyodide single-column tree data and events."""
from .._tree import TreeData, TreeNode
from .widgets import BrowserNode


class Tree(TreeData, BrowserNode):
    wire_type = 'Tree'
    native_event = 'tree'

    def _render_tree(self):
        self.runtime.wake()

    def properties(self):
        state = self.tree_state
        if len(state.entries) > 10001:
            raise ValueError('Browser Tree supports at most 10000 nodes')
        return dict(nodes=[dict(id=key, parent=e.parent, text=e.text)
                           for key, e in state.entries.items() if key],
                    expanded=sorted(state.expanded), selected=state.selected,
                    expandable=state.expandable)

    def handle_native(self, data):
        return self.tree_event(data['item'], data['action'])
