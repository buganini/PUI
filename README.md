# Example

## Code
``` python
class Node(PUI):
    def __init__(self, text=""):
        super().__init__()
        self.text = text

    def comment(self):
        return self.text

def build_ui():
    with PUINode() as pui:
        with Node() as scope:
            for i in range(3):
                Node(f"loop {i}")
        Node()
    return pui
    
print(build_ui())
```

## Result
```
PUINode {
  Node {
    Node {
      # loop 0

    },
    Node {
      # loop 1

    },
    Node {
      # loop 2

    }
  },
  Node {

  }
}
```