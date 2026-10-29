"""Single-column tree composed from native Flet controls."""
import flet as ft
from .base import FBase, colour
from .._tree import TreeData, TreeNode


class Tree(TreeData, FBase):
    def update(self, prev):
        if prev is not None:
            self.ui, self.list, self.rows = prev.ui, prev.list, prev.rows
        else:
            self.list = ft.ListView(spacing=0, padding=0, expand=True)
            self.ui = ft.KeyboardListener(content=self.list)
            self.rows = {}
        self.ui.on_key_down = self._key
        self.ui.on_key_repeat = self._key
        super().update(prev)

    def _handler(self, key, action):
        async def handle(event):
            node = self.get_node()
            if node.destroyed or key not in node.tree_state.entries:
                return
            if action == 'toggle':
                actual = 'collapsed' if key in node.tree_state.expanded else 'expanded'
            else:
                actual = action
            node.tree_event(key, actual)
            node.ui.update()
            await node.ui.focus()
        return handle

    def _render_tree(self):
        state = self.tree_state
        self.rows = {k: row for k, row in self.rows.items() if k in state.entries}
        controls = []
        for key, depth in state.visible():
            entry = state.entries[key]
            if key not in self.rows:
                arrow = ft.IconButton(width=32, height=32, padding=0)
                label = ft.Text()
                hit = ft.GestureDetector(content=ft.Container(content=label, padding=6), expand=True)
                row = ft.Container(content=ft.Row([arrow, hit], spacing=0))
                self.rows[key] = row
            row = self.rows[key]
            arrow, hit = row.content.controls
            arrow.icon = ft.Icons.EXPAND_MORE if key in state.expanded else ft.Icons.CHEVRON_RIGHT
            arrow.opacity = 1 if entry.children else 0
            arrow.disabled = not (entry.children and state.expandable)
            arrow.tooltip = ('Collapse' if key in state.expanded else 'Expand') if entry.children else None
            arrow.on_click = self._handler(key, 'toggle')
            hit.on_tap = self._handler(key, 'clicked')
            hit.on_double_tap = self._handler(key, 'dblclicked')
            label = hit.content.content
            label.value = entry.text
            label.color = colour(self.style_color)
            label.size = self.style_fontsize
            label.font_family = self.style_fontfamily
            row.padding = ft.Padding.only(left=depth * 20)
            row.bgcolor = ft.Colors.SECONDARY_CONTAINER if state.selected == key else None
            controls.append(row)
        self.list.controls = controls

    def _request_tree(self, action, value):
        node = self.get_node()
        if node.ui is None or node.destroyed:
            return super()._request_tree(action, value)
        # Public commands can run from the application's callback worker.
        app = node.root.application()
        def apply():
            current = node.get_node()
            if current.destroyed:
                return
            current._tree_action(action, value)
            current._render_tree()
            current.ui.update()
        app.loop.call_soon_threadsafe(apply)
        return self

    async def _key(self, event):
        node = self.get_node()
        if node.destroyed:
            return
        state = node.tree_state
        visible = [key for key, _ in state.visible()]
        if not visible:
            return
        current = state.selected if state.selected in visible else visible[0]
        index = visible.index(current)
        key = event.key.lower().replace(' ', '')
        action, target = 'selected', current
        if key in ('arrowdown', 'down'):
            target = visible[min(len(visible)-1, index+1)]
        elif key in ('arrowup', 'up'):
            target = visible[max(0, index-1)]
        elif key == 'home':
            target = visible[0]
        elif key == 'end':
            target = visible[-1]
        elif key in ('arrowright', 'right'):
            if current not in state.expanded:
                action = 'expanded'
            elif state.entries[current].children:
                target = state.entries[current].children[0]
        elif key in ('arrowleft', 'left'):
            if current in state.expanded:
                action = 'collapsed'
            else:
                target = state.entries[current].parent or current
        elif key in ('enter', 'space'):
            action = 'clicked'
        else:
            return
        node.tree_event(target, action)
        node.ui.update()
