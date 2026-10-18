from .. import *

import wx

def int_to_wx_colour(color_int):
    red = (color_int >> 16) & 0xFF
    green = (color_int >> 8) & 0xFF
    blue = color_int & 0xFF
    return wx.Colour(red, green, blue)

def getWindow(n):
    p = n
    while p is not None:
        # A layout may be hosted in a native pane inside its PUI container.
        if isinstance(p.ui, wx.Sizer) and p.ui.GetContainingWindow() is not None:
            return p.ui.GetContainingWindow()
        if isinstance(p.ui, wx.Window):
            return p.inner
        if p.parent is p:
            break
        p = p.parent
    raise RuntimeError("!!! getWindow returns None for", n.key if n else None)

class WxPUIView(PUIView):
    def _publish_state_ref(self, name, value):
        from . import state_ref_publish
        state_ref_publish(name, value)

    pui_virtual = True
    def __init__(self):
        super().__init__()

    def sync(self):
        super().sync()
        # An independently redrawn virtual view also changes its native parent's
        # children, but the shared DOM sync only finalizes the virtual view.
        if not self.destroyed and self.pui_dom_parent is not None:
            parent = self.pui_dom_parent.get_node()
            if parent is not self and not parent.destroyed:
                parent.postSync()

    def destroy(self, direct):
        if direct and isinstance(self.ui, wx.Window):
            self.ui.Destroy()
        self.destroyed = True
        self.dirty = self.updating = False
        super().destroy(direct)

    def redraw(self):
        if self.retired_by or self.destroyed:
            return
        self.dirty = True
        if self.updating:
            return
        self.updating = True
        wx.CallAfter(self.sync)

class WXBase(PUINode):
    def get_poster(self):
        from ..poster import make_poster
        import math
        return make_poster(wx.CallAfter, lambda delay, callback: wx.CallLater(math.ceil(delay * 1000), callback))

    scroll = False
    container_x = False # axis
    container_y = False # axis
    expand_x_prio = 0
    expand_y_prio = 0
    cached_wxparent = None

    @property
    def expand_x(self):
        parent = self.wxparent
        if parent and parent.container_x and self.layout_weight is not None:
            return 4 if self.layout_weight > 0 else 0
        return self.expand_x_prio

    @property
    def expand_y(self):
        parent = self.wxparent
        if parent and parent.container_y and self.layout_weight is not None:
            return 4 if self.layout_weight > 0 else 0
        return self.expand_y_prio

    def wxMinSize(self):
        return (
            self.layout_width if self.layout_width is not None else -1,
            self.layout_height if self.layout_height is not None else -1,
        )

    def applyLayoutSize(self, target):
        if target is not None:
            target.SetMinSize(self.wxMinSize())

    def update(self, prev):
        self.cached_wxparent = self.wxparent
        super().update(prev)

    def postUpdate(self):
        super().postUpdate()
        if isinstance(self.ui, wx.Window):
            from .drop import DropTarget
            target = self.ui.GetDropTarget()
            if self._onDropped or self._onDragEntered:
                if isinstance(target, DropTarget):
                    target.node = self
                else:
                    self.ui.SetDropTarget(DropTarget(self))
            elif isinstance(target, DropTarget):
                self.ui.SetDropTarget(None)

    @property
    def wxparent(self):
        parent = self.parent
        while parent is not None and not isinstance(parent, WXBase):
            if parent is parent.parent:
                return None
            parent = parent.parent
        return parent

    def releaseRetiredRefs(self):
        self.cached_wxparent = None
        super().releaseRetiredRefs()

    def destroy(self, direct):
        self.cached_wxparent = None
        super().destroy(direct)


class WxBaseWidget(WXBase):
    pui_terminal = True

    def __init__(self):
        super().__init__()
        self.layout_padding = (3, 3, 3, 3)

    def update(self, prev):
        super().update(prev)

        if prev and prev.ui:
            self.native_style = prev.native_style
        else:
            self.native_style = (wx.Font(self.ui.GetFont()),
                                 self.ui.GetForegroundColour(),
                                 self.ui.GetBackgroundColour())
        font, foreground, background = self.native_style
        font = wx.Font(font)
        if self.style_fontsize is not None:
            font.SetPointSize(self.style_fontsize)
        if self.style_fontfamily is not None:
            font.SetFaceName(self.style_fontfamily)
        if self.style_fontweight is not None:
            font.SetWeight(wx.FONTWEIGHT_BOLD if self.style_fontweight == 'bold'
                           else wx.FONTWEIGHT_NORMAL)
        self.ui.SetFont(font)
        # self.ui.SetForegroundColour(foreground if self.style_color is None
        #                             else int_to_wx_colour(self.style_color))
        self.ui.SetOwnForegroundColour(foreground if self.style_color is None
                                       else int_to_wx_colour(self.style_color))
        # On macOS the native default can be a transparent colour sentinel.
        # Writing it back explicitly disables the system-painted background.
        if self.style_bgcolor is not None:
            self.ui.SetBackgroundColour(int_to_wx_colour(self.style_bgcolor))
            self.ui._pui_background_customized = True
        elif getattr(self.ui, '_pui_background_customized', False):
            self.ui.SetBackgroundColour(wx.NullColour)
            self.ui._pui_background_customized = False

        self.ui.pui_node = self
        self.applyLayoutSize(self.ui)

    def _preClicked(self):
        from .textfield import TextField
        focused = wx.Window.FindFocus()
        node = getattr(focused, "pui_node", None)
        if isinstance(node, TextField):
            node.get_node().commit()
            getWindow(node.parent).SetFocus()

    def destroy(self, direct):
        if direct and self.ui is not None:
            self.ui.Destroy()
        self.destroyed = True
        super().destroy(direct)

class WxBaseLayout(WXBase):
    def __init__(self):
        super().__init__()
        self.relayout = False
        if not isinstance(self.non_virtual_parent, WxBaseLayout):
            self.layout_padding = (11,11,11,11)

    def destroy(self, direct):
        if direct and self.ui is not None:
            self.ui.Clear(delete_windows=True)
        self.sizerItems = []
        super().destroy(direct)

    def update(self, prev):
        if prev and prev.ui:
            self.sizerItems = prev.sizerItems
        else:
            self.sizerItems = []
        super().update(prev)
        self.applyLayoutSize(self.ui)

    def applyChildLayoutSize(self, child, target):
        if target is not None:
            target.SetMinSize(child.wxMinSize())

    def updateSizerItems(self):
        items = []
        for child, si in self.sizerItems:
            child = child.get_node()
            items.append((child, si))
        self.sizerItems[:] = items
        return self.sizerItems

    def postUpdate(self):
        super().postUpdate()
        self.applyChildren()

    def applyChildren(self):
        items = self.updateSizerItems()
        max_x = max((c.expand_x for c, _ in items), default=0)
        max_y = max((c.expand_y for c, _ in items), default=0)
        for child, si in items:
            cross_expand = child.expand_y if self.container_x else child.expand_x
            alignment = wx.ALIGN_CENTER_VERTICAL if self.container_x else wx.ALIGN_LEFT
            si.SetFlag(wx.EXPAND if cross_expand else alignment)
            main_expand = (child.expand_x == max_x and max_x > 0) if self.container_x else (child.expand_y == max_y and max_y > 0)
            proportion = child.layout_weight
            if proportion is None:
                proportion = 1 if main_expand else 0
            si.SetProportion(max(0, int(proportion)))
            if hasattr(si, 'padding_items'):
                top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
                for item, size in zip(si.padding_items, ((0, top), (right, 0), (0, bottom), (left, 0))):
                    item.SetMinSize(size)
                self.applyChildLayoutSize(child, si.content_item)
            else:
                self.applyChildLayoutSize(child, si)

    def paddedChild(self, child):
        # Sizer borders accept one scalar; nested spacers preserve all four sides.
        outer = wx.BoxSizer(wx.VERTICAL)
        top = outer.Add((0, 0))
        row = wx.BoxSizer(wx.HORIZONTAL)
        left = row.Add((0, 0))
        content = row.Add(child.outer, 1, wx.EXPAND)
        right = row.Add((0, 0))
        outer.Add(row, 1, wx.EXPAND)
        bottom = outer.Add((0, 0))
        return outer, row, content, (top, right, bottom, left)

    def addChild(self, idx, child):
        if child.pui_outoforder:
            return
        from .layout import Spacer
        if isinstance(child, Spacer):
            si = self.ui.InsertStretchSpacer(idx)
        elif isinstance(child, (WxBaseLayout, WxBaseWidget)):
            outer, row, content, padding = self.paddedChild(child)
            si = self.ui.Insert(idx, outer)
            si.content_row = row
            si.content_item = content
            si.padding_items = padding
        else:
            return
        self.sizerItems.insert(idx, (child, si))
        self.relayout = True

    def removeChild(self, idx, child):
        if child.pui_outoforder:
            return
        if idx >= len(self.sizerItems):
            return
        _, si = self.sizerItems.pop(idx)
        if hasattr(si, 'content_row'):
            si.content_row.Detach(child.outer)
            self.ui.Remove(idx)
        else:
            self.ui.Remove(idx)
        self.relayout = True

    def postSync(self):
        if self.ui:
            self.applyChildren()
            self.ui.Layout()
            self.relayout = False
            parent = self.wxparent
            if parent is not None and parent is not self and parent.ui:
                parent.ui.Layout()
        super().postSync()


class WxSingleChild(WxBaseWidget):
    """Native window with one content widget/sizer (Window and Scroll)."""
    pui_terminal = False

    @property
    def content_mount(self):
        return self._content_state[0]

    @content_mount.setter
    def content_mount(self, value):
        self._content_state[0] = value

    def update(self, prev):
        # DOM sync may mount children through the previous node during reuse.
        self._content_state = prev._content_state if prev else [None]
        super().update(prev)

    def addChild(self, idx, child):
        if child.pui_outoforder:
            return
        outer, row, content, padding = WxBaseLayout.paddedChild(self, child)
        self.inner.SetSizer(outer, deleteOld=False)
        self.content_mount = (child, row, content, padding)

    def removeChild(self, idx, child):
        if child.pui_outoforder or self.content_mount is None:
            return
        _, row, _, _ = self.content_mount
        row.Detach(child.outer)
        self.inner.SetSizer(None, deleteOld=True)
        self.content_mount = None

    def postSync(self):
        if self.content_mount is not None:
            child, row, content, padding = self.content_mount
            child = child.get_node()
            self.content_mount = (child, row, content, padding)
            top, right, bottom, left = child.layout_padding or (0, 0, 0, 0)
            for item, size in zip(padding, ((0, top), (right, 0), (0, bottom), (left, 0))):
                item.SetMinSize(size)
            content.SetMinSize(child.wxMinSize())
        self.inner.Layout()
        super().postSync()


class WxWindowState:
    """Constructor-equivalent setters for the initial native window state."""
    def maximize(self, enabled=True):
        self._initial_maximize = enabled
        return self

    def fullscreen(self, enabled=True):
        self._initial_fullscreen = enabled
        return self
