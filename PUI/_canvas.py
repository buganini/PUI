"""Shared Canvas enums, memory images and optional painter scopes."""
from __future__ import annotations
from ._path import PathOp, FillRule
from ._rgba import RGBAImage


class CanvasScope:
    PathOp = PathOp
    FillRule = FillRule
    supports_path_clip = False

    def loadRGBA(self, width, height, data):
        """Create a detached, immutable top-to-bottom RGBA byte resource."""
        return RGBAImage(width, height, data)

    def clipRect(self, x, y, width, height):
        """Not implemented on Flet/Tkinter: intentionally a no-op."""
        pass

    def clipPath(self, path, fillRule=FillRule.NonZero):
        """Not implemented on Flet/Tkinter: intentionally a no-op."""
        from ._path import path_commands, fill_rule
        path_commands(path)
        fill_rule(fillRule)

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
