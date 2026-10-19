import flet as ft


def observe(node):
    ui = node.outer
    name = 'on_resize' if isinstance(ui, ft.Page) else 'on_size_change'
    previous = getattr(ui, name)

    async def changed(event):
        import inspect
        if previous is not None:
            result = previous(event)
            if inspect.isawaitable(result):
                await result
        width, height = event.width, event.height
        if not isinstance(ui, ft.Page):
            top, right, bottom, left = node.get_node().layout_padding or (0, 0, 0, 0)
            width, height = width - left - right, height - top - bottom
        node._set_size(width, height)

    setattr(ui, name, changed)
    if isinstance(ui, ft.Page) and ui.width is not None and ui.height is not None:
        # Page geometry may already be known before this subscription is added.
        node.root.application().loop.call_soon(node._set_size, ui.width, ui.height)
    return lambda: setattr(ui, name, previous)
