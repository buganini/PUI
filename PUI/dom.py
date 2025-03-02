# dprint = print
dprint = lambda *x: x

def recur_delete(node, child, direct):
    child.destroyed = True
    if not child.pui_virtual:
        for sc in child.children:
            recur_delete(child, sc, False)
    dprint("recur_delete", node.key, child.key, direct)
    child.destroy(direct)

def sortGridDOM(dom):
    dom = [c for c in dom if c.grid_row is not None and c.grid_column is not None]
    return sorted(dom, key=lambda c:(c.grid_row, c.grid_column, c.grid_rowspan, c.grid_columnspan))

def dom_remove_node(dom_parent, offset, child):
    if child.pui_virtual:
        ret = [child]
        for c in child.children:
            ret.extend(dom_remove_node(dom_parent, offset, c))
        return ret
    else:
        dom_parent.removeChild(offset , child)
        return [child]

def dom_add_nodes(dom_parent, offset, children):
    for i, c in enumerate(children):
        dom_parent.addChild(offset+i, c)

def sync(node, dom_parent, offset, oldDOM, newDOM):
    dprint(f"Syncing {node.key} parent={dom_parent.key} offset={offset} old={len(oldDOM)} new={len(newDOM)}")

    if node.pui_grid_layout:
        oldDOM = sortGridDOM(oldDOM)
        newDOM = sortGridDOM(newDOM)

    dprint("  ===OLD===")
    for c in oldDOM:
        dprint(f"   {c.key} virtual={c.pui_virtual} ui={c.ui}")

    dprint("  ===NEW===")
    for c in newDOM:
        dprint(f"   {c.key} virtual={c.pui_virtual}")

    oldMap = [x.key for x in oldDOM]
    newMap = [x.key for x in newDOM]

    node.preSync()
    node.pui_dom_offset = offset
    node.pui_dom_children_num = 0

    tbd = []
    for i, new in enumerate(newDOM):
        dprint(f"sync child {i}, {new.key} dom_parent={dom_parent.key} virtual={new.pui_virtual}")
        new.pui_dom_parent = dom_parent

        while True:
            # Step 1. just matched
            if i < len(oldDOM) and oldMap[i] == new.key: # matched
                dprint(f"MATCHED {i} {new.key}")
                old = oldDOM[i]

                if new.pui_virtual:
                    new.pui_dom_children_num = old.pui_dom_children_num
                    node.pui_dom_children_num += new.pui_dom_children_num
                else:
                    try:
                        new.update(old)
                    except:
                        import traceback
                        print("## <ERROR OF update() >")
                        print(new.key)
                        traceback.print_exc()
                        print("## </ERROR OF update()>")

                    if not new.pui_outoforder:
                        node.pui_dom_children_num += 1

                    if not new.pui_terminal:
                        sync(new, new, 0, old.children, new.children)

                break # finish

            # Step 2. trim removed nodes after common prefix
            trimmed = False
            while i < len(oldDOM) and not oldDOM[i].key in newMap[i:]: # trim old nodes
                dprint(f"TRIM {i} {oldDOM[i].key}")
                old = oldDOM.pop(i)
                oldMap.pop(i)
                tbd.extend(dom_remove_node(dom_parent, offset+i, old))
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

                if new.pui_virtual:
                    node.pui_dom_children_num += sync(new, dom_parent, offset + node.pui_dom_children_num, [], new.children) - i - 1
                else:
                    dprint("addChild", dom_parent.key, offset + node.pui_dom_children_num, new.key)
                    dom_parent.addChild(offset + node.pui_dom_children_num, new)

                    if not new.pui_outoforder:
                        node.pui_dom_children_num += 1

                    if not new.pui_terminal:
                        sync(new, new, 0, [], new.children)

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
                    nodes = dom_remove_node(dom_parent, offset + i, old)
                    dom_add_nodes(dom_parent, offset + len(oldDOM), nodes)
                    oldMap.append(old.key)
                    oldDOM.append(old)

                    # sync will be peformed in next step 1

                    continue # restart

                 # Step 3-2-2. move target node
                else:
                    oldMap.pop(idx)
                    old = oldDOM.pop(idx)

                    if old.pui_virtual:
                        nodes = dom_remove_node(dom_parent, offset+idx, old)
                        dom_add_nodes(dom_parent, offset+i, nodes)
                        node.pui_dom_children_num += sync(new, dom_parent, offset + idx, old.children, new.children) - i - 1
                    else:
                        dom_parent.removeChild(offset+idx, old)

                        try:
                            new.update(old)
                        except:
                            import traceback
                            print("## <ERROR OF update() >")
                            print(new.key)
                            traceback.print_exc()
                            print("## </ERROR OF update()>")

                        dom_parent.addChild(offset + node.pui_dom_children_num, new)
                        if not new.pui_outoforder:
                            node.pui_dom_children_num += 1

                        if not new.pui_terminal:
                            sync(new, new, 0, old.children, new.children)

                    oldDOM.insert(i, None) # placeholder
                    oldMap.insert(i, new.key)

            break # finish

    # Step 4. trim removed trail
    nl = len(newDOM)
    while len(oldDOM) > nl:
        old = oldDOM.pop(nl)
        oldMap.pop(nl)
        tbd.extend(dom_remove_node(dom_parent, offset + nl, old))

    for c in newDOM:
        c.postUpdate()

    node.postSync()

    # release deleted nodes
    for old in tbd:
        recur_delete(node, old, True)

    dprint(f"sync end -> {node.pui_dom_children_num}")
    return node.pui_dom_children_num