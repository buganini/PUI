# dprint = print
dprint = lambda *x: x

def recur_delete(node, child, direct):
    child.destroyed = True
    for sc in child.children:
        recur_delete(child, sc, False)
    child.destroy(direct)

def sync(node, oldDOM, newDOM):
    dprint("syncing", node.key, len(oldDOM), len(newDOM))

    dprint("  ===OLD===")
    for c in oldDOM:
        dprint("   ", c.key)

    dprint("  ===NEW===")
    for c in newDOM:
        dprint("   ", c.key)
    oldMap = [x.key for x in oldDOM]
    newMap = [x.key for x in newDOM]

    tbd = []
    for i,new in enumerate(newDOM):
        while True:
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

            try: # node exists
                idx = oldMap[i+1:].index(new.key)+i+1
                if idx==i+1: # move wrong node
                    oldMap.pop(i)
                    old = oldDOM.pop(i)
                    node.removeChild(i, old)

                    node.addChild(len(oldDOM), old)
                    oldMap.append(old.key)
                    oldDOM.append(old)

                    continue # restart
                else: # move target node
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

            except: # new node
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

            break # finish

    nl = len(newDOM)
    while len(oldDOM) > nl:
        old = oldDOM.pop(nl)
        oldMap.pop(nl)
        node.removeChild(nl, old)
        tbd.append(old)

    for old in tbd:
        recur_delete(node, old, True)
