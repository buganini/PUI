from __future__ import annotations
from ..color import rgb_color
from .. import _typing as _t
from .. import *
from .base import *
from .label import _StyledText
import wx.html
import json
import re
import warnings
from .._url import OpenURL


class _HtmlWindow(wx.html.HtmlWindow):
    def OnLinkClicked(self, link):
        self._pui_html._open_link(link.GetHref())

    def DoGetBestClientSize(self):
        content = self.GetInternalRepresentation()
        if content is None:
            return super().DoGetBestClientSize()
        return wx.Size(content.GetWidth(), content.GetHeight())

class Text(_StyledText):
    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
        self._internal_tag = str(bool(selectable))
        super().__init__()
        self.text = text
        self.selectable = selectable

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.ChangeValue(self.text) if self.selectable else self.ui.SetLabel(self.text)
        else:
            if self.selectable:
                style = wx.TE_READONLY | wx.BORDER_NONE
                self.ui = wx.TextCtrl(getWindow(self.parent), value=self.text,
                                      style=style | wx.TE_MULTILINE)
            else:
                self.ui = self.static_text_type()(getWindow(self.parent), label=self.text)

        super().update(prev)

class Html(WxBaseWidget):
    expand_x_prio = 4
    expand_y_prio = 4

    def __init__(self, text, selectable=False, *, openURL=True):
        super().__init__()
        self.text = text
        self.selectable = selectable
        self.openURL = bool(openURL)

    @staticmethod
    def _create_webview(parent):
        # Lazy import: ordinary wx widgets do not require a browser runtime.
        import wx.html2 as html2
        backend = (html2.WebViewBackendEdge if wx.Platform == '__WXMSW__'
                   else html2.WebViewBackendWebKit)
        if not html2.WebView.IsBackendAvailable(backend):
            raise RuntimeError(f'{backend!r} backend is unavailable')
        view = html2.WebView.New(parent, backend=backend)
        if view is None:
            raise RuntimeError(f'{backend!r} backend could not be created')
        return view

    def _create(self):
        parent = getWindow(self.parent)
        try:
            self.ui = self._create_webview(parent)
            self._webview = True
            import wx.html2 as html2
            self.ui.Bind(html2.EVT_WEBVIEW_NAVIGATING,
                         lambda event, ui=self.ui: ui._pui_html._navigate(event))
            self.ui.Bind(html2.EVT_WEBVIEW_NEWWINDOW,
                         lambda event, ui=self.ui: ui._pui_html._navigate(event))
        except (ImportError, OSError, RuntimeError, wx.PyAssertionError) as error:
            warnings.warn(
                f'PUI wx Html: WebView unavailable ({error}); falling back to '
                'HtmlWindow. Only an HTML subset is supported; browser CSS, '
                'JavaScript and selectable=False are unavailable.',
                RuntimeWarning, stacklevel=3)
            self.ui = _HtmlWindow(parent)
            self._webview = False
        self._source = None

    def _open_link(self, url):
        if self.openURL:
            OpenURL(url)

    def _navigate(self, event):
        # SetPage loads the fragment at about:blank. Never navigate away from it.
        if event.GetURL() == 'about:blank':
            event.Skip()
            return
        event.Veto()
        self._open_link(event.GetURL())

    def _web_source(self):
        from ..color import css_color
        font = self.ui.GetFont()
        foreground = (css_color(self.style_color) if self.style_color is not None
                      else self.ui.GetForegroundColour().GetAsString(wx.C2S_HTML_SYNTAX))
        background = (css_color(self.style_bgcolor) if self.style_bgcolor is not None
                      else self.ui.GetBackgroundColour().GetAsString(wx.C2S_HTML_SYNTAX))
        # CSS defaults inherit into the fragment without overriding authored
        # inline colours. Escape '<' so a font name cannot close the style tag.
        family = json.dumps(font.GetFaceName()).replace('<', r'\3c ')
        css = (f'body {{ margin: 0; color: {foreground}; background: {background}; '
               f'font-family: {family}; font-size: {font.GetFractionalPointSize()}pt; '
               f'font-weight: {font.GetNumericWeight()}; }}')
        if not self.selectable:
            css += 'html { -webkit-user-select: none; user-select: none; }'
        style = '<style>' + css + '</style>'
        source = str(self.text)
        head = re.search(r'<head(?:\s[^>]*)?>', source, re.IGNORECASE)
        if head:
            return source[:head.end()] + style + source[head.end():]
        # A style element before a fragment is parsed into the document head;
        # retain a leading doctype for full documents and standards mode.
        doctype = re.match(r'\s*<!doctype[^>]*>', source, re.IGNORECASE)
        offset = doctype.end() if doctype else 0
        prefix = '' if doctype else '<!doctype html>'
        return prefix + source[:offset] + style + source[offset:]

    def update(self, prev):
        if prev and prev.ui:
            self.ui, self._webview, self._source = prev.ui, prev._webview, prev._source
        else:
            self._create()
        self.ui._pui_html = self
        super().update(prev)
        if self._webview:
            source = self._web_source()
            if source != self._source:
                self.ui.SetPage(source, 'about:blank')
                self._source = source
            return
        # Preserve the existing lightweight renderer when WebView is missing.
        source = self.text
        if self.style_color is not None:
            source = f'<font color="{rgb_color(self.style_color)}">{source}</font>'
        if source != self._source:
            self.ui.SetPage(source)
            self._source = source
        if self.style_bgcolor is not None:
            self.ui.SetBackgroundColour(int_to_wx_colour(self.style_bgcolor))
        self.ui.InvalidateBestSize()

class MarkDown(Text):
    pui_supported = False
