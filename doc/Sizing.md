This document is to elaborate on sizing semantic, not necessarily implemented

```
HBox/VBox { # Hug X, Hug Y

}
```

```
HBox { # Fill X, Hug Y
    Spacer
}

VBox { # Hug X, Fill Y
    Spacer
}
```

```
Scroll() { # Hug X, Fill Y
    VBox {

    }    
}

Scroll { # Fill X, Hug Y
    HBox {

    }    
}
```
