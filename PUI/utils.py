def trbl(d):
    # https://www.w3schools.com/css/css_padding.asp
    if isinstance(d, int) or isinstance(d, float):
        return (d,d,d,d)
    elif len(d) == 4: # top, right, bottom, left
        return d
    elif len(d) == 3: # top, right/left, bottom
        return (d[0], d[1], d[2], d[1])
    elif len(d) == 2: # top/bottom, right/left
        return (d[0], d[1], d[0], d[1])
    else:
        raise RuntimeError(f"Unsupported format: {d}")
    
def trbl2ltrb(d):
    return (d[3], d[0], d[1], d[2])