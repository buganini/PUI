This document is to elaborate on sizing semantic, not necessarily implemented

# Step 1. Top-Dowm
* Initial state: HugX + HugY (Fit to content size)
* If weight is set, strongly expand on main axis (X in HBox, Y in VBox)
    * Spacer is a placeholder with weight=1

# Step 2. Bottom-Up
* The sole child to an expanding container is also expanding with same priority
* A container is weakly expanding if any of its children is expanding
    * Scroll is weakly expanding on scroliing axes
* A weakly expanding element won't be expanding if there is any strongly expanding element (nweak_expand_{x,y})

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
