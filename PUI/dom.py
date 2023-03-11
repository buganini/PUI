def recur_delete(node, child):
    for sc in child.children:
        recur_delete(child, sc)
    node.removeChild(child)
    child.destroy()

def sync(node, oldDOM, newDOM):
    oldMap = [x.key for x in oldDOM]

    for new in newDOM:
        try:
            old_idx = oldMap.index(new.key)
            oldMap[old_idx] = None
            old = oldDOM[old_idx]
            node.removeChild(old)
            new.update(old)
            node.addChild(old)
            sync(new, old.children, new.children)
        except:
            new.update(None)
            node.addChild(new)
            sync(new, [], new.children)

    for i, key in enumerate(oldMap):
        if key:
            old = oldDOM[i]
            recur_delete(node, old)
