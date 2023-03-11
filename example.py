from PUI import *

class Node(PUINode):
    def __init__(self, text=""):
        super().__init__()
        self.text = text

    def comment(self):
        return self.text

@PUI
def nested():
    with PUINode() as pui:
        with Node("a") as scope:
            Node("b")
        Node("c")
    return pui

print(nested().dump())

@PUI
def loop():
    with PUINode() as pui:
        with Node() as scope:
            for i in range(3):
                Node(f"loop {i}")
        Node()
    return pui

print(loop().dump())
