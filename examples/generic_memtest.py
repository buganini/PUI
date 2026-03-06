import sys
sys.path.append("..")
if len(sys.argv)>1:
    backend = sys.argv[1]
else:
    import random
    backend = random.choice(["tkinter", "PySide6", "flet", "textual", "wx"])

print(backend)
if backend == "tkinter":
    from PUI.tkinter import *
elif backend == "PySide6":
    from PUI.PySide6 import *
elif backend == "flet":
    from PUI.flet import *
elif backend == "textual":
    from PUI.textual import *
elif backend == "wx":
    from PUI.wx import *
else:
    raise RuntimeError(f"Unknown backend {backend}")

import psutil

data = State()
class Example(Application):
    def __init__(self):
        super().__init__()
        data.text = "text"
        data.checkbox = True
        data.radio = 1

    def content(self):
        print("content")

        rss_kb = psutil.Process().memory_info().rss // 1024
        with Window(title="blah"):
            with TimelineView(0.5):
                with VBox():
                    Label(f"RSS: {rss_kb} KB")
                    with Scroll():
                        with VBox():
                            Button("Button").click(self.on_button_click)

                            TextField(data("text")).change(self.on_text_change)

                            with ComboBox(text_model=data("text")):
                                for i in range(10):
                                    ComboBoxItem(f"Item {i}")

                            Checkbox("Checkbox", data("checkbox"))

                            RadioButton("Radio 1", 1, data("radio"))
                            RadioButton("Radio 2", 2, data("radio"))
                            RadioButton("Radio 3", 3, data("radio"))

                            Spacer()

    def on_button_click(self, e):
        print("button clicked")

    def on_text_change(self, e):
        print("text changed", e)

root = Example()
root.run()
