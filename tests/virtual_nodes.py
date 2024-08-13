import sys
sys.path.append("..")

from datetime import datetime
from PUI.PySide6 import *

data = State()
data.state = 0

class Subview(PUIView):
    def content(self):
        Label(f"Subview.Label")

class Example(Application):
    def content(self):
        with Window(title="blah"):
            with VBox():
                Subview() # virtual

                with TimelineView(ttl_sec=5): # virtual
                    Label(f"TimlineView.Label {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                Button("Next").click(self.do_next)

    def do_next(self, e):
        data.state += 1

root = Example()
root.run()
