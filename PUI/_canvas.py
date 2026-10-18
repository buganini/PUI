"""Compatibility scopes for painters without a PUI-managed state stack."""
from __future__ import annotations
from . import _typing as _t


class CanvasScope:
    def push(self) -> None:
        """Compatibility no-op; individual drawing calls specify their own styles."""
        pass

    def pop(self) -> None:
        """Compatibility no-op; does not restore backend-native state."""
        pass


class FrameRate:
    """Count completed draws, publishing at most twice per second."""
    def __init__(self):
        self.started = None
        self.frames = 0

    def tick(self):
        from time import perf_counter
        now = perf_counter()
        if self.started is None:
            self.started = now
            return 'FPS: ...'
        self.frames += 1
        elapsed = now - self.started
        if elapsed < 0.5:
            return None
        text = f'FPS: {self.frames / elapsed:.1f}'
        self.started, self.frames = now, 0
        return text
