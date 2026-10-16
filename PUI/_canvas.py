"""Compatibility scopes for painters without a PUI-managed state stack."""


class CanvasScope:
    def push(self):
        """Compatibility no-op; individual drawing calls specify their own styles."""
        pass

    def pop(self):
        """Compatibility no-op; does not restore backend-native state."""
        pass
