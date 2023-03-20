import sys
sys.path.append("..")
from PUI import *

class Node(PUINode):
    def __init__(self, text=""):
        super().__init__()
        self.text = text

    def comment(self):
        return self.text

@PUI
def nested():
    with PUINode():
        with Node("a") as scope:
            Node("b")
        Node("c")

print(nested().dump())

@PUI
def loop():
    with PUINode():
        with Node() as scope:
            for i in range(3):
                Node(f"loop {i}")
        Node()

print(loop().dump())

@PUI
def single():
    Node()

print(single().dump())
