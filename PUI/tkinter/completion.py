"""Suggestions without posting ttk's focus-grabbing dropdown."""
import tkinter as tk


class Completion:
    def __init__(self, node):
        self.node = node
        self.requested = False
        self.popup = tk.Toplevel(node.ui, takefocus=False)
        self.popup.withdraw()
        self.popup.overrideredirect(True)
        self.rows = tk.Listbox(self.popup, exportselection=False, takefocus=False)
        self.rows.pack(fill='both', expand=True)
        self.top = node.ui.winfo_toplevel()
        self.configure_id = self.top.bind("<Configure>", self.reposition, add=True)
        self.indices = []
        self.signature = None
        self.after = None
        self.rows.bind('<ButtonRelease-1>', self.select)
        self.rows.bind('<FocusOut>', self.blur)
        for sequence in ('<Up>', '<Down>', '<Return>', '<Escape>', '<Tab>'):
            node.ui.bind(sequence, self.key, add=True)
        node.ui.bind('<FocusOut>', self.blur, add=True)
        node.ui.bind('<ButtonPress-1>', self.clicked, add=True)

    def reposition(self, event):
        # Toplevel bindings also receive unrelated descendants' layout events.
        if event.widget in (self.top, self.node.ui):
            self.refresh()

    def hide(self, event=None):
        self.requested = False
        self.popup.withdraw()

    def clicked(self, event):
        # Let ttk handle its ordinary arrow menu; keep suggestions for editor clicks.
        if 'arrow' in self.node.ui.identify(event.x, event.y):
            self.hide()

    def refresh(self, show=False):
        if show:
            self.requested = True
        node = self.node
        if node.destroyed or not node.editable or not node.autoexpand or node.disabled:
            self.hide()
            return
        if not self.requested:
            return
        self.indices = list(range(len(node.children)))
        signature = [(i, node.children[i].key, str(node.children[i].text)) for i in self.indices]
        if show or signature != self.signature:
            self.rows.delete(0, 'end')
            for i in self.indices:
                self.rows.insert('end', str(node.children[i].text))
            self.signature = signature
        if not self.indices:
            self.popup.withdraw()
            return
        self.rows.configure(font=node.ui.cget('font'), height=min(8, len(self.indices)))
        width = node.ui.winfo_width()
        height = self.rows.winfo_reqheight()
        x = node.ui.winfo_rootx()
        y = node.ui.winfo_rooty() + node.ui.winfo_height()
        if y + height > node.ui.winfo_screenheight():
            y = max(0, node.ui.winfo_rooty() - height)
        self.popup.geometry(f'{width}x{height}+{x}+{y}')
        self.popup.deiconify()

    def select(self, event=None):
        selection = self.rows.curselection()
        if not selection:
            return 'break'
        node = self.node
        node.notifications['silent'] = True
        try:
            node.ui.current(self.indices[selection[0]])
        finally:
            node.notifications['silent'] = False
        self.hide()
        node.on_selected(None)
        node.ui.focus_set()
        node.ui.icursor('end')
        return 'break'

    def key(self, event):
        if event.keysym == "Escape":
            self.hide()
        if not self.popup.winfo_ismapped():
            return
        if event.keysym in ('Up', 'Down') and self.indices:
            selected = self.rows.curselection()
            step = 1 if event.keysym == 'Down' else -1
            index = (selected[0] + step) % len(self.indices) if selected else (0 if step == 1 else len(self.indices)-1)
            self.rows.selection_clear(0, 'end')
            self.rows.selection_set(index)
            self.rows.see(index)
            return 'break'
        if event.keysym == 'Return' and self.rows.curselection():
            return self.select()
        if event.keysym in ('Escape', 'Tab'):
            self.hide()
            return 'break' if event.keysym == 'Escape' else None

    def blur(self, event):
        def check():
            self.after = None
            # ttk popdowns are Tcl widgets without Python wrappers for focus_get().
            if not self.node.destroyed and str(self.node.ui.tk.call('focus')) not in (str(self.node.ui), str(self.rows)):
                self.hide()
        if self.after is None:
            self.after = self.node.ui.after_idle(check)

    def destroy(self):
        self.top.unbind("<Configure>", self.configure_id)
        if self.after is not None:
            self.node.ui.after_cancel(self.after)
        self.popup.destroy()
