import sys
sys.path.append("..")

from PUI.PySide6 import *
import time

data = State()

view1_cnt = 0
view2_cnt = 0
view3_cnt = 0
view4_cnt = 0

class View4(PUIView):
    def content(self):
        global view4_cnt
        print("View4.content()")
        view4_cnt += 1
        Label(f"View4 refresh={view4_cnt}")
        Button("Redraw View4").click(self.do_redraw)

    def do_redraw(self, e):
        print("redraw", self.key)
        self.redraw()

class View3(PUIView):
    def content(self):
        global view3_cnt
        print("View3.content()")
        view3_cnt += 1
        Label(f"View3 refresh={view3_cnt}")
        Button("Redraw View3").click(self.do_redraw)
        View4()

    def do_redraw(self, e):
        print("redraw", self.key)
        self.redraw()

class View2(PUIView):
    def content(self):
        global view2_cnt
        print("View2.content()")
        view2_cnt += 1
        Label(f"View2 refresh={view2_cnt}")
        Button("Redraw View2").click(self.do_redraw)
        View3()

    def do_redraw(self, e):
        print("redraw", self.key)
        self.redraw()

class View1(Application):
    def content(self):
        global view1_cnt
        print("View1.content()")
        view1_cnt += 1
        with Window(title="blah"):
            with VBox():
                Label("Expected: each counter increases corresponding to redraw request")
                Button("Reset").click(self.do_reset)
                Label(f"View1 refresh={view1_cnt}")
                Button("Redraw View1").click(self.do_redraw)
                View2()

    def do_redraw(self, e):
        print("redraw", self.key)
        self.redraw()

    def do_reset(self, e):
        global view1_cnt
        global view2_cnt
        global view3_cnt
        view1_cnt = 0
        view2_cnt = 0
        view3_cnt = 0
        self.redraw()

root = View1()
root.run()
