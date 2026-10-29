"""Native ttk tree with retained item identities."""
from .base import TkBaseWidget, ttk, tkFont
from .._tree import TreeData, TreeNode


class Tree(TreeData, TkBaseWidget):
    ttk_style = 'Treeview'

    @property
    def outer(self):
        return self.frame

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui, self.frame = prev.ui, prev.frame
        else:
            self.frame = ttk.Frame(self.tkparent.inner)
            self.frame.grid_rowconfigure(0, weight=1)
            self.frame.grid_columnconfigure(0, weight=1)
            self.ui = ttk.Treeview(self.frame, show='tree', selectmode='browse')
            self.ui.grid(row=0, column=0, sticky='nsew')
            for orient, command, option, row, col, sticky in (
                ('vertical', self.ui.yview, 'yscrollcommand', 0, 1, 'ns'),
                ('horizontal', self.ui.xview, 'xscrollcommand', 1, 0, 'ew')):
                bar = ttk.Scrollbar(self.frame, orient=orient, command=command)
                bar.grid(row=row, column=col, sticky=sticky)
                self.ui.configure(**{option: bar.set})
            self.ui.bind('<ButtonRelease-1>', lambda e: self._pointer(e, 'clicked'))
            self.ui.bind('<Double-1>', lambda e: self._pointer(e, 'dblclicked'))
            for event, expanded in (('<<TreeviewOpen>>', True), ('<<TreeviewClose>>', False)):
                # Tk 9 supplies the affected item in %d; clicking its indicator
                # no longer necessarily changes focus. Tk 8 uses the focus item.
                command = self.ui.register(lambda item, expanded=expanded: self._expanded(expanded, item))
                self.ui.tk.call('bind', self.ui._w, event, f'{command} %d')
            self.ui.bind('<<TreeviewSelect>>', lambda e: self._selected())
            self.ui.bind('<Return>', lambda e: self.get_node().tree_event(int(self.ui.focus() or 0), 'clicked'))
        super().update(prev)

    def _render_tree(self):
        state, ui = self.tree_state, self.ui
        # Move retained children before deleting removed parents.
        existing = set()
        def collect(parent=''):
            for key in ui.get_children(parent):
                existing.add(key)
                collect(key)
        collect()
        for key, entry in state.entries.items():
            if not key:
                continue
            parent = str(entry.parent) if entry.parent else ''
            index = state.entries[entry.parent].children.index(key)
            if ui.exists(str(key)):
                ui.move(str(key), parent, index)
                ui.item(str(key), text=entry.text, open=key in state.expanded)
            else:
                ui.insert(parent, index, iid=str(key), text=entry.text, open=key in state.expanded)
        for key in existing - {str(k) for k in state.entries}:
            if ui.exists(key):
                ui.delete(key)
        if state.selected is not None:
            ui.selection_set(str(state.selected))
            ui.focus(str(state.selected))
        style = ttk.Style(ui)
        font = tkFont.Font(root=ui, font=style.lookup(ui.cget('style'), 'font') or 'TkDefaultFont')
        width = max([80] + [font.measure(state.entries[k].text) + 24*(depth+1) for k,depth in state.visible()])
        ui.column('#0', width=width, stretch=True)

    def _pointer(self, event, action):
        node = self.get_node()
        if not node.destroyed:
            if action == 'clicked' and getattr(node.ui, '_pui_skip_release', False):
                node.ui._pui_skip_release = False
                return
            if action == 'dblclicked':
                node.ui._pui_skip_release = True
            key = node.ui.identify_row(event.y)
            if key and 'indicator' not in node.ui.identify_element(event.x, event.y):
                node.tree_event(int(key), action)

    def _selected(self):
        node = self.get_node()
        if not node.destroyed:
            selected = node.ui.selection()
            node.tree_state.selected = int(selected[0]) if selected else None

    def _expanded(self, expanded, item):
        node = self.get_node()
        if node.destroyed:
            return
        key = int(item or node.ui.focus() or 0)
        # Open is emitted before Tk changes the native state. Let the class
        # binding finish before dispatching callbacks or restoring the policy.
        def apply():
            current = node.get_node()
            if current.destroyed or key not in current.tree_state.entries:
                return
            if not current.tree_event(key, 'expanded' if expanded else 'collapsed'):
                current._render_tree()
        node.ui.after_idle(apply)
