from .refs import ref_set
from itertools import islice

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

def dom_move_node(parent, source, target, child):
    """Move mounted roots without destroying/remounting native widgets."""
    if not child.pui_virtual:
        if not child.pui_outoforder:
            parent.moveChild(source, target, child)
        return
    def roots(node):
        for child in node.children:
            if child.pui_virtual:
                yield from roots(child)
            elif not child.pui_outoforder:
                yield child
    children = list(roots(child))
    indices = range(len(children)) if source > target else range(len(children) - 1, -1, -1)
    for index in indices:
        parent.moveChild(source + index, target + index, children[index])


def _occurrence_keys(nodes, reverse):
    """Pair equal keys by declaration occurrence, even when visual order flips."""
    indices = [i for i, child in enumerate(nodes) if not child.pui_outoforder]
    if reverse:
        indices.reverse()
    indices.extend(i for i, child in enumerate(nodes) if child.pui_outoforder)
    counts, keys = {}, [None] * len(nodes)
    for index in indices:
        key = nodes[index].key
        occurrence = counts.get(key, 0)
        keys[index] = key, occurrence
        counts[key] = occurrence + 1
    return keys


def _reverse_order(node):
    """Virtual scopes share the order of their physical parent's children."""
    reverse = node.pui_reversed_order
    if node.pui_virtual:
        owner = (node.pui_dom_parent or node.parent).get_node()
        while owner.pui_virtual and owner.parent is not owner:
            owner = owner.parent.get_node()
        if owner is not node and not owner.pui_virtual:
            reverse ^= owner.pui_reversed_order
    return reverse

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


def sync(node, dom_parent, dom_offset, oldVDOM, newVDOM, depth=0, _refreshes=None):
    if _refreshes is None:
        _refreshes = []
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
    old_reverse = node._prev_reversed_order
    reverse = _reverse_order(node)
    orig_dom_children_num = dom_children_num = count_dom_children(oldVDOM)
    dom_children_curr = 0

    if DEBUG:
        print(f"{(depth)*'    '}Syncing {node.key}@{id(node)}#tag={node._tag} parent={dom_parent.key}@{id(dom_parent)}#tag={dom_parent._tag} dom_offset={dom_offset} dom_children_num={dom_children_num} oldNode={len(oldVDOM)} newNode={len(newVDOM)}")

    if node.pui_grid_layout and getattr(node, '_grid_columns', None) is None:
        previous_order = list(oldVDOM)
        if not getattr(node, '_grid_previous_auto', False):
            sort_grid_dom_in_place(oldVDOM)
        if oldVDOM != previous_order:
            invalidate_dom_offsets(dom_parent, node)
        sort_grid_dom_in_place(newVDOM)
    else:
        oldOrdered = [c for c in oldVDOM if not c.pui_outoforder]
        oldOutOfOrdered = [c for c in oldVDOM if c.pui_outoforder]
        newOrdered = [c for c in newVDOM if not c.pui_outoforder]
        newOutOfOrdered = [c for c in newVDOM if c.pui_outoforder]

        # oldVDOM is already in mounted order. Only the new declaration needs
        # reversal; applying the current flag to both trees loses transitions.
        if reverse and not node.pui_grid_layout:
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

    if not node.pui_grid_layout and (old_reverse or reverse):
        oldVMap = _occurrence_keys(oldVDOM, old_reverse)
        newVMap = _occurrence_keys(newVDOM, reverse)
    else:
        oldVMap = [x.key for x in oldVDOM]
        newVMap = [x.key for x in newVDOM]

    if oldVMap != newVMap:
        invalidate_dom_offsets(dom_parent, node)
    node.preSync()

    toBeDeleted = []
    for childIdx, newNode in enumerate(newVDOM):
        if DEBUG:
            print(f"{(depth+1)*'    '}sync child {childIdx}, {newNode.key} dom_parent={dom_parent.key} virtual={newNode.pui_virtual}")
        newNode.pui_dom_parent = dom_parent

        while True:
            # Step 1. just matched
            if childIdx < len(oldVDOM) and oldVMap[childIdx] == newVMap[childIdx]: # matched
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
                    if thawed or oldNode._prev_reversed_order != _reverse_order(oldNode):
                        _refreshes.append((oldNode, thawed))
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
                        num, delta = sync(newNode, dom_parent, dom_offset + dom_children_curr, oldNode.children, newNode.children, depth+1, _refreshes)
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
                            sync(newNode, newNode, 0, oldNode.children, newNode.children, depth+1, _refreshes)

                    if thawed:
                        _refreshes.extend((child, True) for child in newNode.children)
                    oldNode.releaseRetiredRefs()

                break # finish

            # Step 2. trim removed nodes after common prefix
            trimmed = False
            while childIdx < len(oldVDOM) and oldVMap[childIdx] not in newVMap[childIdx:]: # trim old nodes
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
                    matchedIdx = oldVMap.index(newVMap[childIdx], childIdx + 1)
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
                    num, delta = sync(newNode, dom_parent, dom_offset + dom_children_curr, [], newNode.children, depth+1, _refreshes)
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
                        sync(newNode, newNode, 0, [], newNode.children, depth+1, _refreshes)

                invalidate_dom_offsets(dom_parent, node)
                oldVDOM.insert(childIdx, newNode) # put newNode node back for later findDomOffsetForNode
                oldVMap.insert(childIdx, newVMap[childIdx])

            ## Step 3-2. existed node
            else:
                # if the target node is in just next position, requeue the blocker to prevent repositioning every nodes coming after
                # eg. when an element is removed from a long list, do single 3-2-1 instead of many 3-2-2

                ### Step 3-2-1. yield the next position for the target node
                if matchedIdx == childIdx + 1:
                    if DEBUG:
                        print(f"{(depth+1)*'    '}S3-2-1. YIELD {childIdx} {newNode.key} ui={id(newNode.ui) if newNode.ui else None}@{newNode.ui}")
                    requeued_key = oldVMap.pop(childIdx)
                    invalidate_dom_offsets(dom_parent, node)
                    toBeRequeued = oldVDOM.pop(childIdx)
                    n = count_dom_children([toBeRequeued])
                    dom_move_node(dom_parent, dom_offset + dom_children_curr,
                                  dom_offset + dom_children_num - n, toBeRequeued)
                    oldVMap.append(requeued_key)
                    invalidate_dom_offsets(dom_parent, node)
                    oldVDOM.append(toBeRequeued)



                ### Step 3-2-2. move target node
                else:
                    if DEBUG:
                        print(f"{(depth+1)*'    '}S3-2-2. MOVE {matchedIdx} {newNode.key} ui={id(newNode.ui) if newNode.ui else None}@{newNode.ui}")
                    oldNode = oldVDOM[matchedIdx]
                    # oldVDOM tracks the actual mounted order during this pass.
                    # A virtual view's self.children already contains its new
                    # proposal, so searching the owner's tree can miss oldNode.
                    offset = dom_offset + count_dom_children(islice(oldVDOM, matchedIdx))
                    oldVMap.pop(matchedIdx)
                    invalidate_dom_offsets(dom_parent, node)
                    oldVDOM.pop(matchedIdx)
                    dom_move_node(dom_parent, offset, dom_offset + dom_children_curr, oldNode)

                    invalidate_dom_offsets(dom_parent, node)
                    oldVDOM.insert(childIdx, oldNode) # put the old node back for later findDomOffsetForNode
                    oldVMap.insert(childIdx, newVMap[childIdx])

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
        offset = dom_offset + count_dom_children(islice(oldVDOM, nl))
        nodes = dom_remove_node(dom_parent, offset, oldNode)
        dom_children_num -= len([n for n in nodes if not n.pui_virtual and not n.pui_outoforder])
        toBeDeleted.append(oldNode)

    for c in newVDOM:
        c.postUpdate()

    node.postSync()
    if node.pui_virtual and (dom_parent.pui_grid_layout or dom_parent.pui_reflow_children):
        dom_parent.get_node().postSync()

    # release deleted nodes
    for oldNode in toBeDeleted:
        recur_delete(node, oldNode, True)

    if DEBUG:
        print(f"{(depth)*'    '}sync end {node.key} -> {dom_children_curr},{dom_children_num}")

    if dom_children_curr != dom_children_num:
        raise VDomError(f"dom_children_curr != dom_children_num for {node.key} -> {dom_children_curr},{dom_children_num}")
    node._prev_reversed_order = reverse
    if depth == 0:
        for child, thawed in _refreshes:
            if thawed:
                _refresh_thawed(child)
            elif (not child.destroyed and not child.retired_by and not child._is_frozen()
                  and child._prev_reversed_order != _reverse_order(child)):
                # Reconcile this retained view. Its virtual descendants perform
                # the same check; physical containers stop inherited reversal.
                child.redraw()
    return dom_children_curr, dom_children_num - orig_dom_children_num
