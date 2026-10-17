"""Process-local named node references. Access only from the UI thread."""

refs = {}
_owners = {}


def ref(name: str):
    """Return the current binder; raise KeyError for an unregistered name."""
    return refs[name]


class NodeBinder:
    """Follow a reconciled node without prescribing backend operations."""
    def __init__(self, node, post=None):
        self.node = node
        self._post = post

    def _node(self, enabled):
        if not isinstance(enabled, bool):
            raise TypeError('Window state must be a bool')
        node = self.node.get_node()
        if node is None or node.destroyed:
            raise RuntimeError('The referenced node has been destroyed')
        return node

    def _schedule(self, enabled, operation):
        self._node(enabled)  # Validate before submitting; do not touch native UI here.

        def invoke():
            node = self.node.get_node()
            if node is not None and not node.destroyed:
                operation(node, enabled)

        try:
            self._post(invoke)
        except RuntimeError:
            # The native dispatcher/event loop may have closed during submission.
            node = self.node.get_node()
            if node is not None and not node.destroyed:
                raise


def ref_set(node):
    if node._ref is None:
        return
    binder = node.__pui_binder__()
    _owners[node._ref] = node
    refs[node._ref] = binder


def ref_clear(node):
    if node._ref is not None and _owners.get(node._ref) is node:
        _owners.pop(node._ref)
        refs.pop(node._ref, None)
