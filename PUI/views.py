"""Shared declaration and selection contract for backend Views containers."""
from .state import DummyBinding


class ViewsMixin:
    pui_terminal = False

    def __init__(self, model=None):
        super().__init__()
        self._owns_model = model is None
        self.model = DummyBinding(None) if model is None else model
        if not hasattr(self.model, 'value'):
            raise TypeError('Views model must be a binding with a value attribute')
        self._validate_selection(self.model.value)

    @staticmethod
    def _validate_selection(key):
        if key is not None and (not isinstance(key, str) or not key):
            raise ValueError('Views selection must be a non-empty string or None')

    def __exit__(self, ex_type, value, traceback):
        try:
            if ex_type is None:
                children = list(self.children)
                keys = [child._id for child in children]
                if any(not isinstance(key, str) or not key for key in keys):
                    raise ValueError('Each Views child needs a non-empty string .id()')
                if len(set(keys)) != len(keys):
                    raise ValueError('Views child IDs must be unique')
                self.children = []
                for child in children:
                    # Give each declared view its own native page, including
                    # virtual views that render zero or multiple root controls.
                    with self._page().id(child._id) as page:
                        content = self._page_content(page)
                        child.parent = content
                        content.children.append(child)
        finally:
            super().__exit__(ex_type, value, traceback)

    def _page_content(self, page):
        return page

    def update(self, prev):
        if prev is not None and self._owns_model and prev._owns_model:
            self.model = prev.model
        super().update(prev)

    def select(self, key):
        """Select a child ID, or None for an empty container, through the model."""
        self._validate_selection(key)
        node = self.get_node()
        if node.destroyed:
            return self
        node.model.value = key
        node = node.get_node()
        if not node.destroyed and node.ui is not None:
            node.root.redraw()
        return self

    def postSync(self):
        super().postSync()
        key = self.model.value
        self._validate_selection(key)
        index = next((i for i, page in enumerate(self.children) if page._id == key), None)
        self._show_view(index)
