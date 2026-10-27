from .base import FBase, FView, ft
from .._modal import ModalMixin


class Modal(ModalMixin, FBase):
    def update(self, prev):
        if prev is not None:
            self.ui, self.dialog, self._page = prev.ui, prev.dialog, prev._page
        else:
            self.ui = ft.Column(tight=True)
            self._page = FView.application(self).ui
            self.dialog = ft.AlertDialog(modal=True, content=self.ui, open=False)
            self._page.overlay.append(self.dialog)
        super().update(prev)
        self.dialog.content = self.shell
        self.dialog.title = ft.Text(self.title) if self.title else None
        if self.preferred_size is not None:
            self.shell.width, self.shell.height = self.preferred_size
        self.dialog.on_dismiss = self._on_dismiss

    async def _on_dismiss(self, event):
        # Flutter reports false for programmatic closes.
        if event.data is not False:
            self.get_node()._dismiss()

    def _set_modal(self, opened):
        if self.ui is None:
            return
        self.dialog.open = opened
        self._transition(opened)

    def addChild(self, idx, child):
        self.ui.controls.insert(idx, child.outer)

    def removeChild(self, idx, child):
        self.ui.controls.remove(child.outer)

    def destroy(self, direct):
        self.dialog.on_dismiss = None
        if self.dialog in self._page.overlay:
            self._page.overlay.remove(self.dialog)
        super().destroy(direct)
