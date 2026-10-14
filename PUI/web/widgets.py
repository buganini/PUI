"""Initial Web widgets backed by retained, serializable element records."""
from dataclasses import dataclass, field
from ..node import PUINode
from ..view import PUIView as BaseView
from .protocol import ProtocolError

_current_runtime = None


def color(value):
    if value is None:
        return None
    if type(value) is int and 0 <= value <= 0xffffff:
        return '#%06x' % value
    raise ValueError('Web colors currently require RGB integers')


@dataclass
class Element:
    id: str
    node: object
    children: list = field(default_factory=list)
    events: dict = field(default_factory=dict)
    attachments: dict = field(default_factory=dict)


class PUIView(BaseView):
    def __init__(self, *args):
        self.runtime = _current_runtime
        super().__init__(*args)

    def redraw(self):
        if self.retired_by or self.destroyed:
            return
        self.dirty = True
        if self.runtime is not None:
            self.runtime.queue_view(self)
        else:
            super().redraw()


class Application(PUIView):
    def update(self, prev=None):
        if self.ui is None:
            self.ui = Element('application', self)
        super().update(prev)

    def addChild(self, idx, child):
        self.ui.children.insert(idx, child.ui)

    def removeChild(self, idx, child):
        self.ui.children.remove(child.ui)

    def quit(self):
        if self.runtime is not None:
            self.runtime.quit_requested = True
            self.runtime.wake()

    def run(self, *, host='127.0.0.1', port=8000, base_url='/', mount_path=None,
            session_ttl=900):
        from .server import serve
        import sys
        module = type(self).__module__
        if module == '__main__':
            spec = sys.modules[module].__spec__
            if spec is None:
                raise ValueError('Use an importable Application class or python -m PUI.web module:Class')
            module = spec.name
        serve(module + ':' + type(self).__qualname__, host=host, port=port,
              base_url=base_url, mount_path=mount_path, session_ttl=session_ttl)


class WebNode(PUINode):
    pui_terminal = True
    wire_type = None

    def __init__(self):
        self.runtime = _current_runtime
        if self.runtime is None:
            raise RuntimeError('Web widgets must be built inside a session worker')
        super().__init__()

    def update(self, prev):
        self.ui = prev.ui if prev is not None else Element(self.runtime.identifier('n'), self)
        self.ui.node = self
        super().update(prev)

    def addChild(self, idx, child):
        self.ui.children.insert(idx, child.ui)

    def removeChild(self, idx, child):
        self.ui.children.remove(child.ui)

    def properties(self):
        return {}


class VBox(WebNode):
    pui_terminal = False
    wire_type = 'VBox'


class HBox(VBox):
    wire_type = 'HBox'


class Window(VBox):
    wire_type = 'Window'

    def __init__(self, title='', icon=None, size=None, maximize=False, fullscreen=False):
        super().__init__()
        if icon is not None or fullscreen:
            raise NotImplementedError('Web icons and fullscreen commands are not implemented')
        self.title = str(title)
        if size is not None:
            self.layout(width=size[0], height=size[1])
        # A Web Window occupies its browser viewport; maximize has no OS effect.

    def properties(self):
        return {'title': self.title}


class Label(WebNode):
    wire_type = 'Label'

    def __init__(self, text, selectable=False):
        super().__init__()
        self.text, self.selectable = str(text), bool(selectable)

    def properties(self):
        return {'text': self.text, 'selectable': self.selectable}


class Button(WebNode):
    wire_type = 'Button'

    def __init__(self, text, *, enabled=True):
        super().__init__()
        self.text, self.enabled = str(text), bool(enabled)

    def properties(self):
        return {'text': self.text, 'enabled': self.enabled}


class TextField(WebNode):
    wire_type = 'TextField'

    def __init__(self, model, edit_model=None, *, placeholder=None):
        super().__init__()
        self.model, self.edit_model = model, edit_model
        self.placeholder = '' if placeholder is None else str(placeholder)

    def properties(self):
        return {'text': str(self.model.value), 'placeholder': self.placeholder}


class Text(WebNode):
    wire_type = 'Text'

    def __init__(self, text):
        super().__init__()
        self.text = str(text)

    def properties(self):
        return {'text': self.text}


class Spacer(WebNode):
    wire_type = 'Spacer'

    def __init__(self):
        super().__init__()
        self.layout(weight=1)


class Divider(WebNode):
    wire_type = 'Divider'


class Scroll(VBox):
    wire_type = 'Scroll'

    def __init__(self, vertical=None, horizontal=False):
        super().__init__()
        self.vertical, self.horizontal = vertical, horizontal

    def properties(self):
        def policy(value):
            return 'auto' if value is None else 'scroll' if value else 'hidden'
        return {'vertical': policy(self.vertical), 'horizontal': policy(self.horizontal)}


class Unsupported:
    pui_supported = False

    def __init__(self, *args, **kwargs):
        raise NotImplementedError('This component is not implemented by the Web backend')


Html = MarkDown = Canvas = Image = Grid = Stack = Checkbox = RadioButton = Unsupported
ComboBox = ComboBoxItem = ProgressBar = Tabs = Tab = Views = Table = Tree = Unsupported
Splitter = Dialog = Confirm = Prompt = MatplotlibCanvas = Unsupported
Combobox = ComboBox
ComboboxItem = ComboBoxItem
