from PUI import *

class Node(PUI):
    def __init__(self, text=""):
        super().__init__()
        self.text = text

    def comment(self):
        return self.text

def nested():
    with PUI() as pui:
        with Node("a") as scope:
            Node("b")
        Node("c")
    return pui

print(nested())

def loop():
    with PUI() as pui:
        with Node() as scope:
            for i in range(3):
                Node(f"loop {i}")
        Node()
    return pui
    
print(loop())
