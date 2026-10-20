"""Editable choices displayed below the editor, using public Flet controls."""
from .base import ft, FView


class Completion:
    def __init__(self, node):
        self.node = node
        self.requested = False
        self.highlighted = None
        self.signature = None
        self.rows = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO)
        self.popup = ft.Container(
            self.rows, visible=False, bgcolor=ft.Colors.SURFACE,
            border=ft.Border.all(1, ft.Colors.OUTLINE))
        self.arrow = ft.GestureDetector(ft.Icon(ft.Icons.ARROW_DROP_DOWN), on_tap=self.toggle)
        self.editor = ft.TextField(suffix_icon=self.arrow)
        self.editor.on_change = self.changed
        self.editor.on_blur = self.blur
        self.editor.on_submit = self.submitted
        # Candidate rows do not take focus. Override Flutter's default outside
        # pointer unfocus so a held click isn't lost before its tap callback.
        self.editor.on_tap_outside = lambda event: None
        self.control = ft.KeyboardListener(
            ft.GestureDetector(ft.Column([self.editor, self.popup], spacing=0),
                               on_tap=self.close), on_key_down=self.key)

    def update_page(self):
        app = FView.application(self.node)
        if app is not None and app.ready and not app.destroyed and not self.node.destroyed:
            app.ui.update()

    def close(self, event=None):
        self.requested = False
        self.highlighted = None
        self.popup.visible = False
        self.update_page()

    def refresh(self):
        node = self.node
        if node.destroyed or not node.editable or node.ui.disabled:
            self.requested = False
        signature = [(child.key, str(child.text)) for child in node.children]
        if signature != self.signature:
            self.highlighted = None
            self.signature = signature
            self.rows.controls = [
                ft.GestureDetector(
                    ft.Container(ft.Text(str(child.text), style=node.ui.text_style),
                                 padding=10),
                    data=child.key, on_tap=self.clicked)
                for child in node.children]
        for i, row in enumerate(self.rows.controls):
            row.content.content.style = node.ui.text_style
            row.content.bgcolor = (ft.Colors.SECONDARY_CONTAINER
                                   if i == self.highlighted else None)
        self.popup.height = min(8, len(node.children)) * 40
        self.popup.visible = bool(self.requested and node.children)
        self.arrow.disabled = node.ui.disabled

    def changed(self, event):
        if self.node.destroyed or self.node.ui.disabled:
            return
        # A programmatic selection is applied once. Do not keep reapplying its
        # old caret position on each subsequent typed-text update.
        self.editor.selection = None
        self.requested = self.node.autoexpand
        self.highlighted = None
        self.node.on_text_change(event)
        self.refresh()
        self.update_page()

    def blur(self, event):
        self.close()

    def toggle(self, event):
        if self.node.ui.disabled:
            return
        self.requested = not self.requested
        self.refresh()
        self.update_page()

    async def clicked(self, event):
        key = event.control.data
        index = next((i for i, child in enumerate(self.node.children) if child.key == key), None)
        if index is not None:
            await self.choose(index)

    async def choose(self, index):
        node = self.node
        if node.destroyed or node.ui.disabled or not 0 <= index < len(node.children):
            return
        self.requested = False
        self.highlighted = None
        node._select(index)
        self.popup.visible = False
        self.update_page()
        await self.editor.focus()
        if self.node.destroyed or not self.node.editable:
            return
        text = self.editor.value or ''
        self.editor.selection = ft.TextSelection(base_offset=len(text), extent_offset=len(text))
        self.update_page()
        self.editor.selection = None

    async def submitted(self, event):
        if self.popup.visible and self.highlighted is not None:
            await self.choose(self.highlighted)
        else:
            self.close()

    def key(self, event):
        if self.node.destroyed or self.node.ui.disabled:
            return
        key = event.key.replace(' ', '').lower()
        if key == 'escape':
            self.close()
        elif key in ('arrowdown', 'arrowup') and self.node.children:
            self.requested = True
            step = 1 if key == 'arrowdown' else -1
            count = len(self.node.children)
            self.highlighted = ((self.highlighted + step) % count if self.highlighted is not None
                                else 0 if step == 1 else count - 1)
            self.refresh()
            self.update_page()
