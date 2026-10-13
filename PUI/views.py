"""Shared declaration and selection contract for backend Views containers."""
from .selection import SelectionModelMixin


class ViewsMixin(SelectionModelMixin):
    pui_terminal = False

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

    def postSync(self):
        super().postSync()
        key = self.model.value
        self._validate_selection(key)
        index = next((i for i, page in enumerate(self.children) if page._id == key), None)
        self._show_view(index)
