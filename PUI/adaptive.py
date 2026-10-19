"""Shared parent-size visibility bounds."""


def matches(size, limits):
    if size is None:
        return False
    width, height = size
    low_w, high_w, low_h, high_h = limits
    return ((low_w is None or width >= low_w) and
            (high_w is None or width < high_w) and
            (low_h is None or height >= low_h) and
            (high_h is None or height < high_h))
