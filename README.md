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
    with PUI() as pui:
        with Node() as scope:
            for i in range(3):
                Node(f"loop {i}")
        Node()
    return pui
    
print(build_ui())
```

## Result
```
PUI { # example.py:21
  Node { # example.py:22
    Node { # example.py:24
      # loop 0

    },
    Node { # example.py:24
      # loop 1

    },
    Node { # example.py:24
      # loop 2

    }
  },
  Node { # example.py:25

  }
}
```