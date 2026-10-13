import sys
sys.path.append("..")
from PUI import *

class Node(PUINode):
    def __init__(self, text=""):
        super().__init__()
        self.text = text

    def comment(self):
        return self.text

class Nested(PUIView):
    def content(self):
        with PUINode():
            with Node("a") as scope:
                Node("b")
            Node("c")

print(Nested().dump())

class Loop(PUIView):
    def content(self):
        with PUINode():
            with Node() as scope:
                for i in range(3):
                    Node(f"loop {i}")
            Node()

print(Loop().dump())

class Single(PUIView):
    def content(self):
        Node()

print(Single().dump())
