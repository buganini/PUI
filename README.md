# Example

## Code
``` python
def setContent():
    with PUI() as pui:
        with HStack("a") as scope:
            HStack("b")
        HStack("c")
        return pui
    
print(setContent())
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