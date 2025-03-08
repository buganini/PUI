DEBUG = False

class VDomError(Exception):
    pass

def recur_delete(node, child, direct):
    child.destroyed = True
    for sc in child.children:
        if sc is not None:
            recur_delete(child, sc, False)
    if DEBUG:
        print("recur_delete", node.key, child.key, direct)
    child.destroy(direct)

def sortGridDOMInPlace(dom):
    dom[:] = [c for c in dom if c.grid_row is not None and c.grid_column is not None]
    dom.sort(key=lambda c:(c.grid_row, c.grid_column, c.grid_rowspan, c.grid_columnspan))

def dom_remove_node(dom_parent, dom_offset, child):
    if child.pui_virtual:
        ret = [child]
        for c in child.children:
            ret.extend(dom_remove_node(dom_parent, dom_offset, c))
        return ret
    else:
        dom_parent.removeChild(dom_offset , child)
        return [child]

def dom_add_nodes(dom_parent, dom_offset, children):
    for childIdx, c in enumerate([n for n in children if not n.pui_virtual]):
        dom_parent.addChild(dom_offset+childIdx, c)

def countDomChildren(nodes):
    num = 0
    for c in nodes:
        if c.pui_virtual:
            num += countDomChildren(c.children)
        elif not c.pui_outoforder:
            num += 1
    return num

def sync(node, dom_parent, dom_offset, oldVDOM, newVDOM, depth=0):
    orig_dom_children_num = dom_children_num = countDomChildren(oldVDOM)
    dom_children_curr = 0

    if DEBUG:
        print(f"{(depth)*'    '}Syncing {node.key}@{id(node)} parent={dom_parent.key}@{id(dom_parent)} dom_offset={dom_offset} dom_children_num={dom_children_num} old={len(oldVDOM)} new={len(newVDOM)}")

    if node.pui_grid_layout:
        sortGridDOMInPlace(oldVDOM)
        sortGridDOMInPlace(newVDOM)

    if DEBUG:
        print(f"{(depth+1)*'    '}===OLD===")
        for c in oldVDOM:
            print(f"{(depth+1)*'    '}{c.key} virtual={c.pui_virtual} ui={c.ui}")

        print(f"{(depth+1)*'    '}===NEW===")
        for c in newVDOM:
            print(f"{(depth+1)*'    '}{c.key} virtual={c.pui_virtual}")

    oldVMap = [x.key for x in oldVDOM]
    newVMap = [x.key for x in newVDOM]

    node.preSync()

    toBeDeleted = []
    for childIdx, new in enumerate(newVDOM):
        if DEBUG:
            print(f"{(depth+1)*'    '}sync child {childIdx}, {new.key} dom_parent={dom_parent.key} virtual={new.pui_virtual}")
        new.pui_dom_parent = dom_parent

        while True:
            # Step 1. just matched
            if childIdx < len(oldVDOM) and oldVMap[childIdx] == new.key: # matched
                if DEBUG:
                    print(f"{(depth+1)*'    '}S1. MATCHED {childIdx} {new.key}")
                old = oldVDOM[childIdx]

                if old.pui_isview: # must also be virtual
                    n = countDomChildren(old.children)
                    dom_children_curr += n
                    if DEBUG:
                        print(f"{(depth+1)*'    '}    dom_children_curr += {n} => {dom_children_curr} dom_children_num={dom_children_num}")

                    old.parent = new.parent
                    old.pui_dom_parent = new.pui_dom_parent
                    newVDOM[childIdx] = old
                    new.destroy(True) # deregister old view from PUIView.__ALLVIEWS__
                else:
                    try:
                        new.update(old)
                    except:
                        import traceback
                        print("## <ERROR OF update() >")
                        print(new.key)
                        traceback.print_exc()
                        print("## </ERROR OF update()>")

                    if new.pui_virtual:
                        num, delta = sync(new, node, dom_offset + dom_children_curr, old.children, new.children, depth+1)
                        dom_children_curr += num
                        dom_children_num += delta
                        if DEBUG:
                            print(f"{(depth+2)*'    '}dom_children_curr += {num} => {dom_children_curr} dom_children_num += {delta} => {dom_children_num}")
                    else:
                        if not new.pui_outoforder:
                            dom_children_curr += 1
                            if DEBUG:
                                print(f"{(depth+2)*'    '}dom_children_curr += 1 => {dom_children_curr} dom_children_num={dom_children_num}")

                        if not new.pui_terminal:
                            sync(new, new, 0, old.children, new.children, depth+1)

                break # finish

            # Step 2. trim removed nodes after common prefix
            trimmed = False
            while childIdx < len(oldVDOM) and not oldVDOM[childIdx].key in newVMap[childIdx:]: # trim old nodes
                if DEBUG:
                    print(f"{(depth+1)*'    '}S2. TRIM {childIdx} {oldVDOM[childIdx].key}")
                old = oldVDOM.pop(childIdx)
                oldVMap.pop(childIdx)
                nodes = dom_remove_node(dom_parent, dom_offset + dom_children_curr, old)
                n = len([n for n in nodes if not n.pui_virtual and not n.pui_outoforder])
                dom_children_num -= n
                if DEBUG:
                    print(f"{(depth+2)*'    '}dom_children_num -= {n} => {dom_children_num}")
                toBeDeleted.extend(nodes)
                trimmed = True

            if trimmed:
                continue # restart

            # Step 3. setup target node

            try:
                matchedIdx = oldVMap[childIdx+1:].index(new.key) + childIdx + 1
            except ValueError:
                matchedIdx = None

            ## Step 3-1. new node
            if matchedIdx is None:
                if DEBUG:
                    print(f"{(depth+1)*'    '}S3-1. NEW {childIdx} {new.key}")
                # always populate new node regardless of isview or not
                try:
                    new.update(None)
                except:
                    import traceback
                    print("## <ERROR OF update() >")
                    print(new.key)
                    traceback.print_exc()
                    print("## </ERROR OF update()>")

                if new.pui_virtual:
                    num, delta = sync(new, dom_parent, dom_offset + dom_children_curr, [], new.children, depth+1)
                    dom_children_curr += num
                    dom_children_num += num
                    if DEBUG:
                        print(f"{(depth+2)*'    '}dom_children_curr += {num} => {dom_children_curr} dom_children_num += {num} => {dom_children_num}")
                else:
                    if DEBUG:
                        print(f"{(depth+1)*'    '}addChild", dom_parent.key, dom_offset + dom_children_curr, new.key)
                    dom_parent.addChild(dom_offset + dom_children_curr, new)

                    if not new.pui_outoforder:
                        dom_children_curr += 1
                        dom_children_num += 1
                        if DEBUG:
                            print(f"{(depth+2)*'    '}dom_children_curr += 1 => {dom_children_curr} dom_children_num += 1 => {dom_children_num}")

                    if not new.pui_terminal:
                        sync(new, new, 0, [], new.children, depth+1)

                oldVDOM.insert(childIdx, new) # put new node back for later findDomOffsetForNode
                oldVMap.insert(childIdx, new.key)

            ## Step 3-2. existed node
            else:
                # if the target node is in just next position, requeue the blocker to prevent repositioning every nodes coming after
                # eg. when an element is removed from a long list, do single 3-2-1 instead of many 3-2-2

                ### Step 3-2-1. yield the next position for the target node
                if matchedIdx == childIdx + 1:
                    if DEBUG:
                        print(f"{(depth+1)*'    '}S3-2-1. YIELD {childIdx} {new.key}")
                    oldVMap.pop(childIdx)
                    toBeRequeued = oldVDOM.pop(childIdx)
                    nodes = dom_remove_node(dom_parent, dom_offset + dom_children_curr, toBeRequeued)
                    n = len([n for n in nodes if not n.pui_virtual and not n.pui_outoforder])
                    dom_add_nodes(dom_parent, dom_children_num - n, nodes)
                    oldVMap.append(toBeRequeued.key)
                    oldVDOM.append(toBeRequeued)

                ### Step 3-2-2. move target node
                else:
                    if DEBUG:
                        print(f"{(depth+1)*'    '}S3-2-2. MOVE {childIdx} {new.key}")
                    oldVMap.pop(matchedIdx)
                    old = oldVDOM.pop(matchedIdx)
                    found, offset = dom_parent.findDomOffsetForNode(old)
                    if not found:
                        raise VDomError(f"findDomOffsetForNode() failed for {old.key} on {dom_parent.key}")
                    nodes = dom_remove_node(dom_parent, offset, old)
                    dom_add_nodes(dom_parent, dom_offset + dom_children_curr, nodes)

                    oldVDOM.insert(childIdx, new) # put new node back for later findDomOffsetForNode
                    oldVMap.insert(childIdx, new.key)

                continue # restart, sync will be peformed in next step 1

            break # finish

    # Step 4. trim removed trail
    nl = len(newVDOM)
    while len(oldVDOM) > nl:
        old = oldVDOM.pop(nl)
        oldVMap.pop(nl)
        nodes = dom_remove_node(dom_parent, dom_offset + nl, old)
        dom_children_num -= len([n for n in nodes if not n.pui_virtual and not n.pui_outoforder])
        toBeDeleted.extend(nodes)

    for c in newVDOM:
        c.postUpdate()

    node.postSync()

    # release deleted nodes
    for old in toBeDeleted:
        recur_delete(node, old, True)

    if DEBUG:
        print(f"{(depth)*'    '}sync end {node.key} -> {dom_children_curr},{dom_children_num}")

    if dom_children_curr != dom_children_num:
        raise VDomError(f"dom_children_curr != dom_children_num for {node.key} -> {dom_children_curr},{dom_children_num}")
    return dom_children_curr, dom_children_num - orig_dom_children_num