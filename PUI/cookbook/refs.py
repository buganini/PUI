from .config import *
import PUI


class RefsExample(PUIView):
    def setup(self):
        self.state = State()
        self.state.posted = 0

    def post_increment(self, event):
        # Obtain the poster on the UI thread, after the node is mounted.
        node = PUI.ref('cookbook.refs.poster').node
        post = node.get_poster()
        post(self.increment, delay=500)  # Pass the callback; do not call increment() here.

    def increment(self):
        # This callback runs on the backend's UI/event loop.
        if not self.get_node().destroyed:
            self.state.posted += 1

    def select_page(self, event, name):
        # Every backend exports the same lookup function: ref is PUI.ref.
        ref('cookbook.refs.tabs').select(name)

    # The main Window is declared with .ref('cookbook.window') in app.py.
    def maximize_window(self, event):
        PUI.ref('cookbook.window').maximize(True)

    def unmaximize_window(self, event):
        PUI.ref('cookbook.window').maximize(False)

    def minimize_window(self, event):
        PUI.ref('cookbook.window').minimize(True)

    def enter_fullscreen(self, event):
        PUI.ref('cookbook.window').fullscreen(True)

    def exit_fullscreen(self, event):
        PUI.ref('cookbook.window').fullscreen(False)

    def content(self):
        with VBox():
            Label('Fixed ref names identify live nodes across updates.')
            Button('Increment after 500 ms').ref('cookbook.refs.poster').click(self.post_increment)
            Label(f'Callbacks executed on the UI loop: {self.state.posted}')
            with HBox():
                Button('Select first').click(self.select_page, 'first')
                Button('Select second').click(self.select_page, 'second')
            with Tabs().ref('cookbook.refs.tabs').layout(weight=1):
                with Tab('First').id('first'):
                    Label('Every binder stores its original node in .node.')
                with Tab('Second').id('second'):
                    Label('Window refs return an imperative window binder.')
            Label('Window controls (desktop backends only). Restore a minimized window using your desktop.')
            desktop = PUI_BACKEND in ('PySide6', 'wx', 'tkinter', 'flet')
            with HBox():
                Button('Maximize', disabled=not desktop).click(self.maximize_window)
                Button('Unmaximize', disabled=not desktop).click(self.unmaximize_window)
                Button('Minimize', disabled=not desktop).click(self.minimize_window)
            with HBox():
                Button('Fullscreen', disabled=not desktop).click(self.enter_fullscreen)
                Button('Exit fullscreen', disabled=not desktop).click(self.exit_fullscreen)
