import sys
sys.path.append("..")

from PUI.PySide6 import *
import time

data = State()
data.show = True
data.count1 = 0
data.count2 = 0

class View1(PUIView):
    def content(self):
        for i in range(data.count1):
            Label(f"View1-{i}")

class View2(PUIView):
    def content(self):
        for i in range(data.count2):
            Label(f"View2-{i}")

class App(Application):
    def content(self):
        with Window(title="blah"):
            with VBox():
                with HBox():
                    Button("-").click(self.do_decrease1)
                    Button("+").click(self.do_increase1)
                View1()

                with HBox():
                    Button("Hide").click(self.do_hide)
                    Button("Show").click(self.do_show)

                if data.show:
                    Label("*****")

                with HBox():
                    Button("-").click(self.do_decrease2)
                    Button("+").click(self.do_increase2)
                View2()

    def do_hide(self, e):
        data.show = False

    def do_show(self, e):
        data.show = True

    def do_decrease1(self, e):
        data.count1 -= 1

    def do_increase1(self, e):
        data.count1 += 1

    def do_decrease2(self, e):
        data.count2 -= 1

    def do_increase2(self, e):
        data.count2 += 1

root = App()
root.run()
