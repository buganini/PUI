"""Optional selection models shared by Views and Tabs."""
from .state import DummyBinding


class SelectionModelMixin:
    def __init__(self, model=None):
        super().__init__()
        self._owns_model = model is None
        self.model = DummyBinding(None) if model is None else model
        if not hasattr(self.model, 'value'):
            raise TypeError('Selection model must be a binding with a value attribute')
        self._validate_selection(self.model.value)

    @staticmethod
    def _validate_selection(key):
        if key is not None and (not isinstance(key, str) or not key):
            raise ValueError('Selection must be a non-empty string or None')

    def update(self, prev):
        if prev is not None and self._owns_model and prev._owns_model:
            self.model = prev.model
        super().update(prev)

    def select(self, key):
        """Write the selected key through the current model and redraw."""
        self._validate_selection(key)
        node = self.get_node()
        if node.destroyed:
            return self
        node.model.value = key
        node = node.get_node()
        if not node.destroyed and node.ui is not None:
            node.root.redraw()
        return self


class TabsMixin(SelectionModelMixin):
    pui_terminal = False

    @staticmethod
    def _validate_selection(key):
        if key is not None and not isinstance(key, str):
            raise ValueError('Tabs selection must be a string or None')

    def update(self, prev):
        self._selection_status = prev._selection_status if prev else {
            'syncing': False, 'applied': None, 'initialized': False,
        }
        if prev and self._owns_model and not prev._owns_model:
            self._selection_status['initialized'] = False
        super().update(prev)

    @staticmethod
    def _tab_key(tab):
        return tab._id or str(tab.label)

    def preSync(self):
        self._selection_status['syncing'] = True
        super().preSync()

    def _selected_index(self):
        key = self.model.value
        self._validate_selection(key)
        if not self.children:
            return None
        return next((i for i, tab in enumerate(self.children)
                     if self._tab_key(tab) == key), 0)

    def postSync(self):
        index = self._selected_index()
        if self._owns_model and not self._selection_status['initialized'] and index is not None:
            if self.model.value is None:
                self.model.value = self._tab_key(self.children[index])
            self._selection_status['initialized'] = True
        self._show_tab(index)
        self._selection_status['applied'] = index
        self._selection_status['syncing'] = False
        super().postSync()

    def _native_selected(self, index):
        node = self.get_node()
        if node.destroyed or node.ui is None or node._selection_status['syncing']:
            return
        if index is None or not 0 <= index < len(node.children):
            return
        if index != node._selection_status['applied']:
            node.select(node._tab_key(node.children[index]))
