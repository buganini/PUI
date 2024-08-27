import sys
sys.path.append("../../../PUI")

from datetime import datetime
from PUI.textual import *

n = 100

class Test(Application):
    def content(self):
        with Window(title="blah"):
            with VBox():
                Label(f"Scroll {n}")
                with HBox().layout(weight=1):
                    with Scroll():
                        with VBox():
                            for i in range(n):
                                Label(f"{i}")

root = Test()
root.run()

s = root.serialize(layout_debug=True, show_key=False)
print(s)
