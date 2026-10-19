from textual.events import Resize, Mount


def observe(node, ui=None):
    ui = node.ui if ui is None else ui
    closed = False
    subscribed = False

    def measure():
        if not node.get_node().destroyed and ui.is_mounted:
            size = ui.content_size
            node._set_size(size.width, size.height)

    def message(event):
        if isinstance(event, (Resize, Mount)):
            ui.call_after_refresh(measure)

    def attach():
        nonlocal subscribed
        if not closed and ui.is_running:
            ui.message_signal.subscribe(ui, message, immediate=True)
            subscribed = True
            measure()

    ui.call_after_refresh(attach)
    def close():
        nonlocal closed
        closed = True
        if subscribed:
            ui.message_signal.unsubscribe(ui)
    return close
