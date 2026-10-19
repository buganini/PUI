from .refs import ref_set

DEBUG = False

class VDomError(Exception):
    pass

def recur_delete(node, child, direct):
    child.destroyed = True
    child._dom_offset_cache = None
    for sc in child.children:
        if sc is not None:
            # Virtual nodes have no native owner to destroy their children.
            # Pass destruction through them until a native subtree owns it.
            recur_delete(child, sc, direct and child.pui_virtual)
    if DEBUG:
        print("recur_delete", node.key, child.key, direct)
    child.destroy(direct)

def sort_grid_dom_in_place(dom):
    dom[:] = [c for c in dom if c.grid_row is not None and c.grid_column is not None]
    dom.sort(key=lambda c:(c.grid_row if c.grid_row is not None else -1, c.grid_column if c.grid_column is not None else -1, c.grid_rowspan if c.grid_rowspan is not None else -1, c.grid_columnspan if c.grid_columnspan is not None else -1))

def dom_remove_node(dom_parent, dom_offset, child):
    if DEBUG:
        print(f"dom_remove_node key={child.key} virtual={child.pui_virtual} children={len(child.children)} dom_parent={dom_parent.key} dom_offset={dom_offset}")
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

def count_dom_children(nodes):
    num = 0
    for c in nodes:
        if c.pui_virtual:
            num += count_dom_children(c.children)
        elif not c.pui_outoforder:
            num += 1
    return num

def invalidate_dom_offsets(parent, scope):
    """Invalidate flattened offsets through virtual containers to their owner."""
    # A virtual scope can be queried directly as well as through its native
    # owner. Its logical ancestors may be skipped by pui_dom_parent.
    current = scope
    while current is not None and current is not parent:
        current._dom_offset_version = object()
        if not current.pui_virtual or current.parent is current:
            break
        current = current.parent
    while parent is not None:
        parent._dom_offset_version = object()
        if not parent.pui_virtual:
            break
        ancestor = parent.pui_dom_parent
        if ancestor is parent:
            break
        parent = ancestor


def _refresh_thawed(node):
    if node.destroyed or node.retired_by or node._is_frozen():
        return
    if node.pui_isview:
        node.redraw()
    for child in list(node.children):
        _refresh_thawed(child)


def sync(node, dom_parent, dom_offset, oldVDOM, newVDOM, depth=0, _thaws=None):
    if _thaws is None:
        _thaws = []
    if node.pui_frozen:
        # Discard only newly built proposals, never the mounted subtree. In
        # particular, unregister unmounted PUIViews and their references.
        retained = {id(child) for child in oldVDOM}
        for child in list(newVDOM):
            if id(child) not in retained:
                recur_delete(node, child, False)
        newVDOM[:] = oldVDOM
        for child in newVDOM:
            child.parent = node
        return count_dom_children(oldVDOM), 0
    if [n.key for n in oldVDOM] != [n.key for n in newVDOM]:
        invalidate_dom_offsets(dom_parent, node)
    orig_dom_children_num = dom_children_num = count_dom_children(oldVDOM)
    dom_children_curr = 0

    if DEBUG:
        print(f"{(depth)*'    '}Syncing {node.key}@{id(node)}#tag={node._tag} parent={dom_parent.key}@{id(dom_parent)}#tag={dom_parent._tag} dom_offset={dom_offset} dom_children_num={dom_children_num} oldNode={len(oldVDOM)} newNode={len(newVDOM)}")

    if node.pui_grid_layout:
        previous_order = list(oldVDOM)
        sort_grid_dom_in_place(oldVDOM)
        if oldVDOM != previous_order:
            invalidate_dom_offsets(dom_parent, node)
        sort_grid_dom_in_place(newVDOM)
    else:
        oldOrdered = [c for c in oldVDOM if not c.pui_outoforder]
        oldOutOfOrdered = [c for c in oldVDOM if c.pui_outoforder]
        newOrdered = [c for c in newVDOM if not c.pui_outoforder]
        newOutOfOrdered = [c for c in newVDOM if c.pui_outoforder]

        if node.pui_reversed_order:
            oldOrdered.reverse()
            newOrdered.reverse()

        if oldVDOM != oldOrdered + oldOutOfOrdered:
            invalidate_dom_offsets(dom_parent, node)
        oldVDOM.clear()
        oldVDOM.extend(oldOrdered + oldOutOfOrdered)
        newVDOM.clear()
        newVDOM.extend(newOrdered + newOutOfOrdered)

    if DEBUG:
        print(f"{(depth+1)*'    '}===OLD===")
        for c in oldVDOM:
            print(f"{(depth+1)*'    '}{c.key}#tag={c._tag} virtual={c.pui_virtual} children={len(c.children)} ui={id(c.ui) if c.ui else None}@{c.ui}")

        print(f"{(depth+1)*'    '}===NEW===")
        for c in newVDOM:
            print(f"{(depth+1)*'    '}{c.key}#tag={c._tag} virtual={c.pui_virtual} children={len(c.children)}")
        print(f"{(depth+1)*'    '}=========")

    oldVMap = [x.key for x in oldVDOM]
    newVMap = [x.key for x in newVDOM]

    node.preSync()

    toBeDeleted = []
    for childIdx, newNode in enumerate(newVDOM):
        if DEBUG:
            print(f"{(depth+1)*'    '}sync child {childIdx}, {newNode.key} dom_parent={dom_parent.key} virtual={newNode.pui_virtual}")
        newNode.pui_dom_parent = dom_parent

        while True:
            # Step 1. just matched
            if childIdx < len(oldVDOM) and oldVMap[childIdx] == newNode.key: # matched
                if DEBUG:
                    print(f"{(depth+1)*'    '}S1. MATCHED {childIdx} {newNode.key} ui={id(newNode.ui) if newNode.ui else None}@{newNode.ui}")
                oldNode = oldVDOM[childIdx]
                thawed = oldNode.pui_frozen and not newNode.pui_frozen

                if oldNode.pui_isview: # must also be virtual
                    n = count_dom_children(oldNode.children)
                    dom_children_curr += n
                    if DEBUG:
                        print(f"{(depth+1)*'    '}    dom_children_curr += {n} => {dom_children_curr} dom_children_num={dom_children_num}")

                    oldNode.pui_frozen = newNode.pui_frozen
                    oldNode.parent = newNode.parent
                    oldNode.pui_dom_parent = newNode.pui_dom_parent
                    newVDOM[childIdx] = oldNode
                    if thawed:
                        _thaws.append(oldNode)
                    newNode.destroy(True) # deregister old view from PUIView.__ALLVIEWS__
                else:
                    try:
                        newNode.update(oldNode)
                    except:
                        import traceback
                        print("## <ERROR OF update() >")
                        print(newNode.key)
                        traceback.print_exc()
                        print("## </ERROR OF update()>")

                    else:
                        ref_set(newNode)

                    if newNode.pui_virtual:
                        num, delta = sync(newNode, node, dom_offset + dom_children_curr, oldNode.children, newNode.children, depth+1, _thaws)
                        dom_children_curr += num
                        dom_children_num += delta
                        if DEBUG:
                            print(f"{(depth+2)*'    '}dom_children_curr += {num} => {dom_children_curr} dom_children_num += {delta} => {dom_children_num}")
                    else:
                        if not newNode.pui_outoforder:
                            dom_children_curr += 1
                            if DEBUG:
                                print(f"{(depth+2)*'    '}dom_children_curr += 1 => {dom_children_curr} dom_children_num={dom_children_num}")

                        if not newNode.pui_terminal:
                            sync(newNode, oldNode, 0, oldNode.children, newNode.children, depth+1, _thaws)

                    if thawed:
                        _thaws.extend(newNode.children)
                    oldNode.releaseRetiredRefs()

                break # finish

            # Step 2. trim removed nodes after common prefix
            trimmed = False
            while childIdx < len(oldVDOM) and not oldVDOM[childIdx].key in newVMap[childIdx:]: # trim old nodes
                if DEBUG:
                    print(f"{(depth+1)*'    '}S2. TRIM {childIdx} {oldVDOM[childIdx].key}")
                invalidate_dom_offsets(dom_parent, node)
                oldNode = oldVDOM.pop(childIdx)
                oldVMap.pop(childIdx)
                nodes = dom_remove_node(dom_parent, dom_offset + dom_children_curr, oldNode)
                n = len([n for n in nodes if not n.pui_virtual and not n.pui_outoforder])
                dom_children_num -= n
                if DEBUG:
                    print(f"{(depth+2)*'    '}dom_children_num -= {n} => {dom_children_num}")
                toBeDeleted.append(oldNode)
                trimmed = True

            if trimmed:
                continue # restart

            # Step 3. setup target node

            matchedIdx = None
            if newNode.pui_movable:
                try:
                    matchedIdx = oldVMap.index(newNode.key, childIdx + 1)
                except ValueError:
                    pass

            ## Step 3-1. new node
            if matchedIdx is None:
                if DEBUG:
                    print(f"{(depth+1)*'    '}S3-1. NEW {childIdx} {newNode.key}")
                # always populate new node regardless of isview or not
                try:
                    newNode.update(None)
                except:
                    import traceback
                    print("## <ERROR OF update() >")
                    print(newNode.key)
                    traceback.print_exc()
                    print("## </ERROR OF update()>")
                else:
                    ref_set(newNode)

                if newNode.pui_virtual:
                    num, delta = sync(newNode, dom_parent, dom_offset + dom_children_curr, [], newNode.children, depth+1, _thaws)
                    dom_children_curr += num
                    dom_children_num += num
                    if DEBUG:
                        print(f"{(depth+2)*'    '}dom_children_curr += {num} => {dom_children_curr} dom_children_num += {num} => {dom_children_num}")
                else:
                    if DEBUG:
                        print(f"{(depth+1)*'    '}addChild", dom_parent.key, dom_offset + dom_children_curr, newNode.key)
                    dom_parent.addChild(dom_offset + dom_children_curr, newNode)

                    if not newNode.pui_outoforder:
                        dom_children_curr += 1
                        dom_children_num += 1
                        if DEBUG:
                            print(f"{(depth+2)*'    '}dom_children_curr += 1 => {dom_children_curr} dom_children_num += 1 => {dom_children_num}")

                    if not newNode.pui_terminal:
                        sync(newNode, newNode, 0, [], newNode.children, depth+1, _thaws)

                invalidate_dom_offsets(dom_parent, node)
                oldVDOM.insert(childIdx, newNode) # put newNode node back for later findDomOffsetForNode
                oldVMap.insert(childIdx, newNode.key)

            ## Step 3-2. existed node
            else:
                # if the target node is in just next position, requeue the blocker to prevent repositioning every nodes coming after
                # eg. when an element is removed from a long list, do single 3-2-1 instead of many 3-2-2

                ### Step 3-2-1. yield the next position for the target node
                if matchedIdx == childIdx + 1:
                    if DEBUG:
                        print(f"{(depth+1)*'    '}S3-2-1. YIELD {childIdx} {newNode.key} ui={id(newNode.ui) if newNode.ui else None}@{newNode.ui}")
                    oldVMap.pop(childIdx)
                    invalidate_dom_offsets(dom_parent, node)
                    toBeRequeued = oldVDOM.pop(childIdx)
                    nodes = dom_remove_node(dom_parent, dom_offset + dom_children_curr, toBeRequeued)
                    n = len([n for n in nodes if not n.pui_virtual and not n.pui_outoforder])
                    dom_add_nodes(dom_parent, dom_children_num - n, nodes)
                    oldVMap.append(toBeRequeued.key)
                    invalidate_dom_offsets(dom_parent, node)
                    oldVDOM.append(toBeRequeued)



                ### Step 3-2-2. move target node
                else:
                    if DEBUG:
                        print(f"{(depth+1)*'    '}S3-2-2. MOVE {matchedIdx} {newNode.key} ui={id(newNode.ui) if newNode.ui else None}@{newNode.ui}")
                    oldNode = oldVDOM[matchedIdx]
                    found, offset = dom_parent.findDomOffsetForNode(oldNode)
                    if not found:
                        raise VDomError(f"S3-2-2: findDomOffsetForNode() failed for {oldNode.key}#tag={oldNode._tag} on {dom_parent.key}#tag={dom_parent._tag} {dom_parent.children}")
                    oldVMap.pop(matchedIdx)
                    invalidate_dom_offsets(dom_parent, node)
                    oldVDOM.pop(matchedIdx)
                    nodes = dom_remove_node(dom_parent, offset, oldNode)
                    dom_add_nodes(dom_parent, dom_offset + dom_children_curr, nodes)

                    invalidate_dom_offsets(dom_parent, node)
                    oldVDOM.insert(childIdx, oldNode) # put the old node back for later findDomOffsetForNode
                    oldVMap.insert(childIdx, oldNode.key)

                continue # restart, sync will be peformed in next step 1

            break # finish

    # Step 4. trim removed trail
    if DEBUG:
        print(f"{(depth+1)*'    '}S4. TRIM")
    nl = len(newVDOM)
    if DEBUG:
        print(f"{(depth+1)*'    '}S4. TRIM", f"dom_offset={dom_offset}", len(oldVDOM), "=>", len(newVDOM))
    while len(oldVDOM) > nl:
        invalidate_dom_offsets(dom_parent, node)
        oldNode = oldVDOM.pop(nl)
        if DEBUG:
            print(f"{(depth+2)*'    '}", f"key={oldNode.key} virtual={oldNode.pui_virtual} children={len(oldNode.children)}")
        oldVMap.pop(nl)
        nodes = dom_remove_node(dom_parent, dom_offset + nl, oldNode)
        dom_children_num -= len([n for n in nodes if not n.pui_virtual and not n.pui_outoforder])
        toBeDeleted.append(oldNode)

    for c in newVDOM:
        c.postUpdate()

    node.postSync()

    # release deleted nodes
    for oldNode in toBeDeleted:
        recur_delete(node, oldNode, True)

    if DEBUG:
        print(f"{(depth)*'    '}sync end {node.key} -> {dom_children_curr},{dom_children_num}")

    if dom_children_curr != dom_children_num:
        raise VDomError(f"dom_children_curr != dom_children_num for {node.key} -> {dom_children_curr},{dom_children_num}")
    if depth == 0:
        for child in _thaws:
            _refresh_thawed(child)
    return dom_children_curr, dom_children_num - orig_dom_children_num
