from .config import *

state = State()
state.password = ""
state.buffered_password = ""
state.editing = ""


class MaskedFieldExample(PUIView):
    def clear(self, event):
        state.password = ""
        state.buffered_password = ""
        state.editing = ""

    def content(self):
        with VBox():
            Label("Password (committed on Enter or blur)")
            MaskedField(state("password"), placeholder="Enter a password")
            Label(f"Committed length: {len(state.password)}")

            Label("Password with an editing buffer")
            MaskedField(state("buffered_password"), state("editing"),
                        placeholder="Enter another password")
            Label(f"Editing length: {len(state.editing)}")
            Label(f"Committed length: {len(state.buffered_password)}")

            Button("Clear passwords").click(self.clear)
            Spacer()
