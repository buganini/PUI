import sys
sys.path.append("..")

from datetime import datetime
from PUI.PySide6 import *

class Subview1(PUIView):
    def content(self):
        Label(f"Subview1.Label")

class Subview3(PUIView):
    def content(self):
        Label(f"Subview3.Label")

class Subview2(PUIView):
    def content(self):
        Subview3()

class TimelineSubview(PUIView):
    def content(self):
        with TimelineView(ttl_sec=5): # virtual
            Label(f"TimlineSubView.Label {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

class VirtualTest(Application):
    def content(self):
        with Window(title="blah"):
            with VBox():
                Subview1() # virtual

                Subview2() # nested-virtual

                TimelineSubview() # nested-virtual

                with TimelineView(ttl_sec=5): # virtual
                    Label(f"TimlineView.Label {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

root = VirtualTest()
root.run()
