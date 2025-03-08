import sys
sys.path.append("..")

from PUI.PySide6 import *
# from PUI.wx import *
import time

data = State()
data.count1 = 1
data.show2 = True
data.count2 = 1
data.count2sub = 1
data.count3 = 1

class View1(PUIView):
    def content(self):
        for i in range(data.count1):
            Label(f"View1-{i}")

class View2Sub(PUIView):
    def content(self):
        with HBox():
            Label(f"View2Sub n={data.count2sub}")
            Button("-").click(self.do_decrease2sub)
            Button("+").click(self.do_increase2sub)
        for i in range(data.count2sub):
            Label(f"View2Sub-{i}")

    def do_decrease2sub(self, e):
        data.count2sub -= 1

    def do_increase2sub(self, e):
        data.count2sub += 1

class View2(PUIView):
    def content(self):
        for i in range(data.count2):
            Label(f"View2-{i}")
        View2Sub()

class View3(PUIView):
    def content(self):
        for i in range(data.count3):
            Label(f"View3-{i}")

class App(Application):
    def content(self):
        with Window(title="blah"):
            with VBox():
                with HBox():
                    Label(f"View1 n={data.count1}")
                    Button("-").click(self.do_decrease1)
                    Button("+").click(self.do_increase1)
                View1()

                with HBox():
                    Label(f"View2 show={data.show2}")
                    Button("Hide").click(self.do_hide)
                    Button("Show").click(self.do_show)

                if data.show2:
                    with HBox():
                        Label(f"View2 n={data.count2}")
                        Button("-").click(self.do_decrease2)
                        Button("+").click(self.do_increase2)
                    View2()

                with HBox():
                    Label(f"View3 n={data.count3}")
                    Button("-").click(self.do_decrease3)
                    Button("+").click(self.do_increase3)
                View3()


    def do_hide(self, e):
        data.show2 = False

    def do_show(self, e):
        data.show2 = True

    def do_decrease1(self, e):
        data.count1 -= 1

    def do_increase1(self, e):
        data.count1 += 1

    def do_decrease2(self, e):
        data.count2 -= 1

    def do_increase2(self, e):
        data.count2 += 1

    def do_decrease3(self, e):
        data.count3 -= 1

    def do_increase3(self, e):
        data.count3 += 1

root = App()
root.run()
