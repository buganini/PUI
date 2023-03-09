# Example

## Code
``` python
def build_ui():
    with PUI() as pui:
        with HStack("a") as scope:
            HStack("b")
        HStack("c")
    return pui
    
print(build_ui())
```

## Result
```
PUI {
  HStack/a {
    HStack/b {

    }
  },
  HStack/c {

  }
}
```