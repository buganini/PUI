from .config import *

class TreeNode():
    def __init__(self, data, parent=None):
        self.data = data
        self.parent = parent
        self.children = []

    def addChild(self, child):
        child.parent = self
        self.children.append(child)

    @property
    def index(self):
        if self.parent is None:
            return 0
        return self.parent.children.index(self)

    def __repr__(self):
        return f'{{"data":"{self.data}", "children":{self.children}}}'

class TreeExample(PUIView):
    class TreeAdapter(BaseTreeAdapter):
        def __init__(self, data):
            self._data = data
            self.adapter = None

        def parent(self, node):
            if node is None:
                return None
            return node.parent

        def child(self, parent, index):
            if parent is None:
                return self._data.value.children[index]
            return parent.children[index]

        def data(self, node):
            return node.data

        def rowCount(self, parent):
            if parent is None:
                return len(self._data.value.children)
            return len(parent.children)

        def clicked(self, node):
            print("clicked", node.data if node else None)

        def dblclicked(self, node):
            print("dblclicked", node.data if node else None)

        def expanded(self, node):
            print("expanded", node.data if node else None)

        def collapsed(self, node):
            print("collapsed", node.data if node else None)

    def setup(self):
        self.state = State()
        self.state.data = TreeNode("Root")

        sub1 = TreeNode("Sub1")
        sub1.addChild(TreeNode("Sub1.1"))
        sub1_2 = TreeNode("Sub1.2")
        sub1_2.addChild(TreeNode("Sub1.2.1"))
        sub1_2.addChild(TreeNode("Sub1.2.2"))
        sub1.addChild(sub1_2)
        sub1.addChild(TreeNode("Sub1.3"))
        self.state.data.addChild(sub1)

        sub2 = TreeNode("Sub2")
        self.state.data.addChild(sub2)

        sub3 = TreeNode("Sub3")
        sub3.addChild(TreeNode("Sub3.1"))
        sub3.addChild(TreeNode("Sub3.2"))
        self.state.data.addChild(sub3)

        print(self.state.data)

        self.adapter = self.TreeAdapter(self.state("data"))

    def content(self):
        with VBox():
            with HBox():
                Button("Add item").click(lambda e: self.add_item())
                Spacer()

            with HBox():
                Tree(self.adapter)
                Tree(self.adapter).expandAll()

    def add_item(self):
        t = TreeNode("New item")
        t.addChild(TreeNode("Sub"))
        self.state.data.addChild(t)
        self.redraw()
