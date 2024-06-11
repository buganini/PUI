# dprint = print
dprint = lambda *x: x

def recur_delete(node, child, direct):
    child.destroyed = True
    for sc in child.children:
        recur_delete(child, sc, False)
    child.destroy(direct)
    dprint("recur_delete", node.key, child, direct)

def sortDOM(dom):
    sorted = []
    ooo = []
    for e in dom:
        if e.outoforder:
            ooo.append(e)
        else:
            sorted.append(e)
    sorted.extend(ooo)
    return sorted

def sortGridDOM(dom):
    dom = [c for c in dom if c.grid_row is not None and c.grid_column is not None]
    return sorted(dom, key=lambda c:(c.grid_row, c.grid_column, c.grid_rowspan, c.grid_columnspan))

def sync(node, oldDOM, newDOM):
    if node.grid_layout:
        oldDOM = sortGridDOM(oldDOM)
        newDOM = sortGridDOM(newDOM)
    oldDOM = sortDOM(oldDOM)
    newDOM = sortDOM(newDOM)
    dprint("syncing", node.key, len(oldDOM), len(newDOM))

    dprint("  ===OLD===")
    for c in oldDOM:
        dprint("   ", c.key)

    dprint("  ===NEW===")
    for c in newDOM:
        dprint("   ", c.key)
    oldMap = [x.key for x in oldDOM]
    newMap = [x.key for x in newDOM]

    node.preSync()

    tbd = []
    for i,new in enumerate(newDOM):
        while True:
            # Step 1. skip common prefix
            if i < len(oldDOM) and oldMap[i] == new.key: # matched
                dprint(f"MATCHED {i} {new.key}")
                old = oldDOM[i]

                try:
                    new.update(old)
                except:
                    import traceback
                    print("## <ERROR OF update() >")
                    print(node.key)
                    traceback.print_exc()
                    print("## </ERROR OF update()>")

                if not new.terminal:
                    sync(new, old.children, new.children)

                break # finish

            # Step 2. trim removed nodes after common prefix
            trimmed = False
            while i < len(oldDOM) and not oldDOM[i].key in newMap: # trim old nodes
                dprint(f"TRIM {i} {oldDOM[i].key}")
                old = oldDOM.pop(i)
                oldMap.pop(i)
                node.removeChild(i, old)
                tbd.append(old)
                trimmed = True

            if trimmed:
                continue # restart

            # Step 3. setup target node
            try:
                idx = oldMap[i+1:].index(new.key)+i+1
            except ValueError:
                idx = None

            # Step 3-1. new node
            if idx is None:
                try:
                    new.update(None)
                except:
                    import traceback
                    print("## <ERROR OF update() >")
                    print(new.key)
                    traceback.print_exc()
                    print("## </ERROR OF update()>")
                if not new.terminal:
                    sync(new, [], new.children)
                node.addChild(i, new)
                oldDOM.insert(i, None) # placeholder
                oldMap.insert(i, new.key)

            # Step 3-2. existed node
            else:
                # if the target node is in just next position, requeue the front to prevent repositioning every nodes coming after
                # eg. when an element is removed from a long list, do single 3-2-1 instead of many 3-2-2

                # Step 3-2-1. yield the next position for the target node
                if idx==i+1:
                    oldMap.pop(i)
                    old = oldDOM.pop(i)
                    node.removeChild(i, old)

                    node.addChild(len(oldDOM), old)
                    oldMap.append(old.key)
                    oldDOM.append(old)

                    # sync will be peformed in next step 1

                    continue # restart

                 # Step 3-2-2. move target node
                else:
                    oldMap.pop(idx)
                    old = oldDOM.pop(idx)
                    node.removeChild(idx, old)

                    try:
                        new.update(old)
                    except:
                        import traceback
                        print("## <ERROR OF update() >")
                        print(node.key)
                        traceback.print_exc()
                        print("## </ERROR OF update()>")

                    if not new.terminal:
                        sync(new, old.children, new.children)

                    node.addChild(i, new)
                    oldDOM.insert(i, None) # placeholder
                    oldMap.insert(i, new.key)
            break # finish

    # Step 4. trim removed trail
    nl = len(newDOM)
    while len(oldDOM) > nl:
        old = oldDOM.pop(nl)
        oldMap.pop(nl)
        node.removeChild(nl, old)
        tbd.append(old)

    for c in newDOM:
        c.postUpdate()

    node.postSync()

    # release deleted nodes
    for old in tbd:
        recur_delete(node, old, True)
