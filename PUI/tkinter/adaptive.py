import tkinter as tk


def observe(node):
    ui = node.ui
    pending = None
    closed = False

    def measure():
        nonlocal pending
        pending = None
        if closed or node.get_node().destroyed:
            return
        if not ui.winfo_ismapped():
            return
        # PUI's Tk layout padding is allocated outside the child widget.
        inset = sum(ui.winfo_pixels(ui.cget(k) or 0) for k in ('borderwidth', 'highlightthickness')
                    if k in ui.keys())
        node._set_size(ui.winfo_width() - 2 * inset, ui.winfo_height() - 2 * inset)

    def schedule(event=None):
        nonlocal pending
        if event is not None and event.widget is not ui:
            return
        if pending is None:
            pending = ui.after_idle(measure)

    configure = ui.bind('<Configure>', schedule, add='+')
    mapped = ui.bind('<Map>', schedule, add='+')
    schedule()
    def close():
        nonlocal closed
        closed = True
        try:
            if pending is not None:
                ui.after_cancel(pending)
            ui.unbind('<Configure>', configure)
            ui.unbind('<Map>', mapped)
        except tk.TclError:
            pass  # Destruction can precede PUI teardown.
    return close
