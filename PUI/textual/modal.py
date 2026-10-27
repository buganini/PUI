from textual.screen import ModalScreen
from textual.containers import Vertical
from .base import TBase
from .._modal import ModalMixin


class _ModalScreen(ModalScreen):
    DEFAULT_CSS = '''
    _ModalScreen { align: center middle; }
    _ModalScreen > Vertical {
        width: 60; max-width: 95%; height: auto; max-height: 95%;
        border: round $primary; padding: 1 2; background: $surface;
    }
    '''
    BINDINGS = [('escape', 'close_modal', 'Close')]

    def __init__(self, node, body):
        super().__init__()
        self.node = node
        self.body = body

    def compose(self):
        yield self.body

    def on_mount(self):
        self.call_after_refresh(lambda: self.node.get_node()._sync_content())

    def on_screen_resume(self):
        node = self.node.get_node()
        if node.destroyed or not node._modal_requested():
            self.app.pop_screen()
            if node.destroyed:
                self.app.uninstall_screen(self)

    def action_close_modal(self):
        self.node.get_node()._dismiss()


class Modal(ModalMixin, TBase):
    # A Screen is mounted asynchronously. Reconcile its content only once the
    # native body is attached; installed screens retain it across close/reopen.
    pui_terminal = True

    def update(self, prev):
        if prev is not None:
            self.ui, self.screen, self._content = prev.ui, prev.screen, prev._content
        else:
            self.ui = Vertical()
            self.screen = _ModalScreen(self, self.ui)
            self._content = {'children': [], 'busy': False}
            self.root.ui.install_screen(self.screen, f'pui-modal-{id(self.screen)}')
        self.screen.node = self
        self.ui.border_title = self.title or ''
        super().update(prev)

    def t_update_layout(self):
        if self.ui is None:
            return
        # Terminal sizing uses tLayout; pixel Window.size does not map to cells.
        self.ui.styles.width = self.tlayout_width or 60
        self.ui.styles.height = self.tlayout_height or 'auto'

    def _sync_content(self):
        if (self.destroyed or self._content['busy'] or not self.ui.is_attached
                or self._content['children'] == self.children):
            return
        from ..dom import sync
        self._content['busy'] = True
        try:
            sync(self, self, 0, self._content['children'], self.children)
            self._content['children'] = list(self.children)
        finally:
            self._content['busy'] = False

    def _set_modal(self, opened):
        if self.ui is None:
            return
        app = self.root.ui if self.root is not None else self.screen.app
        if opened and self.screen not in app.screen_stack:
            app.push_screen(self.screen)
        elif not opened and app.screen is self.screen:
            app.pop_screen()
        self._transition(opened)
        if not self.destroyed:
            self._sync_content()

    def addChild(self, idx, child):
        self.ui.mount(child.outer, before=idx)

    def removeChild(self, idx, child):
        child.tremove()

    def moveChild(self, source, target, child):
        if source < target:
            self.ui.move_child(child.outer, after=target)
        elif source > target:
            self.ui.move_child(child.outer, before=target)

    def destroy(self, direct):
        if self.ui is None:
            return super().destroy(direct)
        app = self.root.ui
        self._set_modal(False)
        if self.screen not in app.screen_stack:
            app.uninstall_screen(self.screen)
        super().destroy(direct)
