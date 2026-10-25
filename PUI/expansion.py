"""Per-axis expansion demand; descendants promote containers only to level 2."""


def physical_children(node):
    for child in node.children:
        child = child.get_node()
        if not child._visible:
            continue
        if child.pui_virtual:
            yield from physical_children(child)
        else:
            yield child


def physical_parent(node):
    parent = node.parent
    while parent is not None and parent is not node and parent.pui_virtual:
        if parent.parent is parent:
            return None
        parent = parent.parent
    return parent if parent is not node else None


def priority(node, axis, parent=None):
    if not node._visible:
        return 0
    if parent is None:
        parent = physical_parent(node)
    terminal = node._terminal_units
    weight = node.tlayout_weight if terminal and node.tlayout_weight is not None else node.layout_weight
    if parent is not None and (getattr(parent, 'container_' + axis, False) or
                               getattr(parent, 'pui_grid_layout', False)) and weight is not None:
        return 5 if weight > 0 else 0
    base_method = getattr(node, '_base_expansion_priority', None)
    base = base_method(axis) if base_method else getattr(node, 'expand_' + axis + '_prio', 0)
    dimension = ('tlayout_' if terminal else 'layout_') + ('width' if axis == 'x' else 'height')
    policy = 'HorizontalPolicy' if axis == 'x' else 'VerticalPolicy'
    if policy in getattr(node, 'qt_params', {}):
        return base
    if base >= 2 or node.pui_terminal or getattr(node, dimension, None) is not None:
        return base
    return max(base, 2 if any(priority(child, axis, node) >= 2
                             for child in physical_children(node)) else 0)
