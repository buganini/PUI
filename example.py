from PUI import *

@PUIElement
def Node(ctx, key, comment=""):
    n = PUI("Node", path=ctx.path+tuple([len(ctx.children)]), key=key, comment=comment)
    return n

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
                Node()
        Node()
    return pui
    
print(loop())
