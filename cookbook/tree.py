from .config import *

class TreeExample(PUIView):
    def content(self):
        with VBox():
            with HBox():
                Button("Add item").click(lambda e: self.add_item())
                Spacer()

            with HBox():
                with Tree().expandAll():
                    with TreeNode("Root"):
                        with TreeNode("Sub 1"):
                            TreeNode("Sub 1-1")
                            TreeNode("Sub 1-2")
                        TreeNode("Sub 2")
                        with TreeNode("Sub 3"):
                            TreeNode("Sub 3-1")

                        self.appendTree(self.state.data)

    def setup(self):
        self.state = State()
        self.state.data = ["Recursive", []]

    def add_item(self):
        self.state.data[1].append(["New item", [
            ["Sub", []]
        ]])
        self.redraw()

    def appendTree(self, node):
        with TreeNode(node[0]):
            for sn in node[1]:
                self.appendTree(sn)
