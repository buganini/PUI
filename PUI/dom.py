# dprint = print
dprint = lambda *x: x

def recur_delete(node, idx, child):
    for sidx,sc in enumerate(child.children):
        recur_delete(child, sidx, sc)
    node.removeChild(idx, child)
    child.destroy()

def sync(node, oldDOM, newDOM):
    dprint("syncing", node.key, len(oldDOM), len(newDOM))
    dprint("  ===OLD===")
    for c in oldDOM:
        dprint("   ", c.key)
    dprint("  ===NEW===")
    for c in newDOM:
        dprint("   ", c.key)
    oldMap = [x.key for x in oldDOM]

    skipHead = 0
    for i in range(0, min(len(oldDOM), len(newDOM))):
        if oldDOM[i].key == newDOM[i].key:
            oldMap[i] = None
            old = oldDOM[i]
            new = newDOM[i]
            try:
                new.update(old)
            except:
                import traceback
                print("## <ERROR OF sync() >")
                print(node.key)
                traceback.print_exc()
                print("## </ERROR OF sync()>")

            if not new.terminal:
                sync(new, old.children, new.children)
            skipHead += 1
        else:
            break

    skipTail = 0
    # for i in range(0, min(len(oldDOM)-skipHead, len(newDOM)-skipHead)):
    #     if oldDOM[-1-i].key == newDOM[-1-i].key:
    #         oldMap[-1-i] = None
    #         old = oldDOM[-1-i]
    #         new = newDOM[-1-i]
    #         new.update(old)
    #         sync(new, old.children, new.children)
    #         skipTail += 1
    #     else:
    #         break

    for i, new in enumerate(newDOM[skipHead:len(newDOM)-skipTail]):
        new_idx = skipHead + i
        try:
            old_idx = oldMap.index(new.key)
        except:
            old_idx = -1
        if old_idx >= 0:
            oldMap[old_idx] = None
            old = oldDOM[old_idx]
            node.removeChild(old_idx, old)
            new.update(old)
            if not new.terminal:
                sync(new, old.children, new.children)
            node.addChild(new_idx, old)
        else:
            new.update(None)
            if not new.terminal:
                sync(new, [], new.children)
            node.addChild(new_idx, new)

    for old_idx, key in enumerate(oldMap):
        if key:
            old = oldDOM[old_idx]
            recur_delete(node, old_idx, old)
