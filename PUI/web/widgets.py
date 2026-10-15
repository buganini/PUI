"""Initial Web widgets backed by retained, serializable element records."""
from dataclasses import dataclass, field
import logging
import math
from ..node import PUINode
from ..view import PUIView as BaseView
from ..views import ViewsMixin
from ..selection import TabsMixin
from ..common import checkbox_get, checkbox_set, combobox_get, combobox_record_selection, combobox_set_text
from ..state import Unstate
from ..node import PUIEvent
from .protocol import SAFE_INTEGER

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
    native_context: object = None


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

    def run(self, **kwargs):
        # The gateway must not build a UI; each client worker creates its own app.
        return self.start(**kwargs)

    def start(self, *, factory=None, auth=None, **kwargs):
        """Start the Web server; forward keyword options to the server runtime.

        Omit factory to use this instance's importable Application class. CLI
        launchers may supply module:Class/factory to defer imports to workers.
        Optional auth(username, password) must return True to allow login.
        """
        from .server import serve
        import sys
        if factory is None:
            module = type(self).__module__
            if module == '__main__':
                spec = sys.modules[module].__spec__
                if spec is None:
                    raise ValueError('Use an importable Application class or python -m PUI.web module:Class')
                module = spec.name
            factory = module + ':' + type(self).__qualname__
        return serve(factory, auth=auth, **kwargs)


class WebNode(PUINode):
    pui_terminal = True
    wire_type = None
    model_roles = ()
    native_event = None

    def native_context(self):
        return None

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
        """Return wire values that remain unchanged after snapshot publication.

        Build new containers for new values; never expose mutable application
        data or edit a previously returned record in place.
        """
        return {}

    def validate_options(self):
        """Reject unsupported declarations before they enter the render stream."""
        for name in ('row', 'column', 'rowspan', 'columnspan'):
            value = getattr(self, 'grid_' + name)
            if value is not None:
                if not isinstance(self.non_virtual_parent, Grid):
                    raise ValueError('Web grid placement requires a Grid parent')
                if type(value) is not int or not (1 if name.endswith('span') else 0) <= value <= 10000:
                    raise ValueError('Web grid positions/spans must be bounded nonnegative integers')
        callbacks = {'dblclick': '_onDblClicked', 'keypress': '_onKeyPress',
            'mousedown': '_onMouseDown', 'mouseup': '_onMouseUp', 'mousemove': '_onMouseMove',
            'mouseenter': '_onMouseEnter', 'mouseleave': '_onMouseLeave', 'wheel': '_onWheel',
            'dragEnter': '_onDragEntered', 'drop': '_onDropped'}
        if not isinstance(self, TextField):
            callbacks.update(input='_onInput', change='_onChanged')
        if isinstance(self, ComboBox):
            callbacks.pop('change')
        if isinstance(self, Canvas):
            for name in self.pointer_handlers:
                callbacks.pop(name, None)
        for name, attribute in callbacks.items():
            if getattr(self, attribute) is not None:
                raise NotImplementedError('Web %s.%s() is not implemented' % (self.wire_type, name))

        def number(value, name, minimum=0):
            if (type(value) not in (int, float) or not minimum <= value <= SAFE_INTEGER or
                    not math.isfinite(value)):
                raise ValueError('Web %s must be a finite number >= %s' % (name, minimum))

        for name in ('width', 'height', 'weight'):
            value = getattr(self, 'layout_' + name)
            if value is not None:
                number(value, 'layout.' + name)
        for name in ('padding', 'margin'):
            value = getattr(self, 'layout_' + name)
            if value is not None:
                for side in value:
                    number(side, 'layout.' + name, -SAFE_INTEGER if name == 'margin' else 0)
        if self.style_fontsize is not None:
            number(self.style_fontsize, 'fontSize')
        weight = self.style_fontweight
        if weight is not None and weight not in ('normal', 'bold'):
            number(weight, 'fontWeight', 1)
            if weight > 1000:
                raise ValueError('Web numeric fontWeight must be between 1 and 1000')
        if self.style_fontfamily is not None and not isinstance(self.style_fontfamily, str):
            raise ValueError('Web fontFamily must be a string')


class VBox(WebNode):
    pui_terminal = False
    wire_type = 'VBox'


class HBox(VBox):
    wire_type = 'HBox'


class Grid(VBox):
    wire_type = 'Grid'
    pui_grid_layout = True


class Stack(VBox):
    wire_type = 'Stack'


class Views(ViewsMixin, VBox):
    wire_type = 'Views'

    def _page(self):
        return VBox().layout(padding=0)

    def _show_view(self, index):
        self.selected = None if index is None else self.children[index].ui.id

    def properties(self):
        return {'selected': self.selected}


class Tabs(TabsMixin, VBox):
    wire_type = 'Tabs'
    model_roles = ('model',)
    native_event = 'select'
    NORTH, SOUTH, EAST, WEST = 'n', 's', 'e', 'w'

    def __init__(self, tabposition=NORTH, model=None):
        super().__init__(model=model)
        if tabposition not in (self.NORTH, self.SOUTH, self.EAST, self.WEST):
            raise ValueError('Unknown tab position')
        self.tabposition = tabposition

    def addChild(self, idx, child):
        if not isinstance(child, Tab):
            raise TypeError('Tabs children must be Tab declarations')
        super().addChild(idx, child)

    def _show_tab(self, index):
        self.selected = None if index is None else self.children[index].ui.id

    def postSync(self):
        if any(not isinstance(child, Tab) for child in self.children):
            raise TypeError('Tabs children must be Tab declarations')
        super().postSync()

    def properties(self):
        return {'selected': self.selected, 'position': self.tabposition}

    def handle_native(self, data):
        index = next((i for i, page in enumerate(self.children) if page.ui.id == data['page_id']), None)
        if index is None:
            return False
        self._native_selected(index)
        return True


class Tab(VBox):
    wire_type = 'Tab'

    def __init__(self, label):
        super().__init__()
        self.label = str(label)
        self.layout(padding=0)

    def properties(self):
        return {'label': self.label}

    def validate_options(self):
        super().validate_options()
        if not isinstance(self.non_virtual_parent, Tabs):
            raise ValueError('Tab requires a Tabs parent')


class Window(VBox):
    wire_type = 'Window'

    def __init__(self, title='', icon=None, size=None, maximize=False, fullscreen=False):
        super().__init__()
        if icon is not None:
            logging.getLogger(__name__).warning('Web Window ignores icon; window icons are not implemented')
        if fullscreen:
            logging.getLogger(__name__).warning('Web Window ignores fullscreen; fullscreen is not implemented')
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
    model_roles = ('model', 'edit_model')

    def __init__(self, model, edit_model=None, *, placeholder=None):
        super().__init__()
        self.model, self.edit_model = model, edit_model
        self.placeholder = '' if placeholder is None else str(placeholder)

    def properties(self):
        return {'text': str(self.model.value), 'placeholder': self.placeholder}


class Checkbox(WebNode):
    wire_type = 'Checkbox'
    model_roles = ('model',)
    native_event = 'toggle'

    def __init__(self, text, model, value=None):
        super().__init__()
        self.text, self.model = str(text), model
        self.value = text if value is None else value

    def properties(self):
        return {'text': self.text, 'checked': bool(checkbox_get(self.model, self.value))}

    def native_context(self):
        return Unstate(self.value)

    def handle_native(self, data):
        checkbox_set(self.model, data['checked'], self.value)
        event = PUIEvent()
        event.value = data['checked']
        self._clicked(event)
        return True


class RadioButton(WebNode):
    wire_type = 'RadioButton'
    model_roles = ('model',)
    native_event = 'activate'

    def __init__(self, text, value, model):
        super().__init__()
        self.text, self.value, self.model = str(text), value, model

    def properties(self):
        return {'text': self.text, 'checked': self.model.value == self.value}

    def native_context(self):
        return Unstate(self.value)

    def handle_native(self, data):
        self.model.value = self.value
        event = PUIEvent()
        event.value = self.value
        self._clicked(event)
        return True


class ComboBox(WebNode):
    wire_type = 'ComboBox'
    pui_terminal = False
    model_roles = ('index_model', 'text_model')
    native_event = 'choose'

    def __init__(self, editable=False, index_model=None, text_model=None, *, enabled=True):
        super().__init__()
        self.editable = bool(editable)
        self.native_event = 'edit' if self.editable else 'choose'
        self.index_model, self.text_model = index_model, text_model
        self.enabled = bool(enabled)
        self.combo_state = {'key': None, 'text': ''}

    def update(self, prev):
        if prev is not None:
            self.combo_state = prev.combo_state
        super().update(prev)

    def postSync(self):
        if any(not isinstance(child, ComboBoxItem) for child in self.children):
            raise TypeError('ComboBox requires ComboBoxItem children')
        super().postSync()

    def properties(self):
        index, text = combobox_get(self.children, self.index_model, self.text_model, self.editable, self.combo_state)
        return {'enabled': self.enabled, 'selected': self.children[index].ui.id if index >= 0 else None,
                'editable': self.editable, 'text': text}

    def native_context(self):
        return [self.editable, [[child.ui.id, child.text, Unstate(child.value)] for child in self.children]]

    def handle_native(self, data):
        if self.editable:
            index = next((i for i, item in enumerate(self.children) if item.text == data['value']), None)
            if index is None:
                combobox_set_text(self.index_model, self.text_model, data['value'], self.combo_state)
                event = PUIEvent()
                event.value = data['value']
                self._change(event)
                return True
        else:
            index = next((i for i, item in enumerate(self.children) if item.ui.id == data['item_id']), None)
            if index is None:
                return False
        if self.index_model is not None:
            self.index_model.value = index
        if self.text_model is not None:
            self.text_model.value = self.children[index].value
        combobox_record_selection(self.children, index, self.combo_state)
        event = PUIEvent()
        event.value = index
        self._change(event)
        return True


class ComboBoxItem(WebNode):
    wire_type = 'ComboBoxItem'

    def __init__(self, text, value=None):
        super().__init__()
        self.text = str(text)
        self.value = text if value is None else value
        self.id(self.text)

    def properties(self):
        return {'text': self.text}

    def validate_options(self):
        super().validate_options()
        if not isinstance(self.non_virtual_parent, ComboBox):
            raise ValueError('ComboBoxItem requires a ComboBox parent')


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


class ProgressBar(WebNode):
    wire_type = 'ProgressBar'

    def __init__(self, progress, maximum=1):
        super().__init__()
        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > SAFE_INTEGER
               for v in (progress, maximum)) or maximum < 0:
            raise ValueError('Web progress requires finite numbers and a nonnegative maximum')
        self.progress, self.maximum = progress, maximum

    def properties(self):
        return {'progress': min(self.maximum, max(0, self.progress)), 'maximum': self.maximum}


class Scroll(VBox):
    wire_type = 'Scroll'
    END = -0.0

    def __init__(self, vertical=None, horizontal=False):
        super().__init__()
        self.vertical, self.horizontal = vertical, horizontal
        self.requests = [None, None]
        self.scroll_state = [None, None]
        self.layout(weight=1)

    def update(self, prev):
        if prev is not None:
            self.scroll_state = list(prev.scroll_state)
        for axis, request in enumerate(self.requests):
            old = self.scroll_state[axis]
            if request is None and prev is not None:
                self.requests[axis] = prev.requests[axis]
            elif request is not None and (prev is None or request != prev.requests[axis]):
                self.scroll_state[axis] = request + [1 if old is None else old[2] + 1]
        super().update(prev)

    def scrollX(self, pos=0):
        return self._request(0, pos)

    def scrollY(self, pos=0):
        return self._request(1, pos)

    def _request(self, axis, pos):
        if type(pos) not in (int, float) or not math.isfinite(pos) or abs(pos) > SAFE_INTEGER:
            raise ValueError('Web scroll offsets must be finite numbers')
        node = self.get_node()
        if node.destroyed:
            return self
        request = ['end' if math.copysign(1, pos) < 0 else 'start', abs(pos)]
        if node.ui is None:
            node.requests[axis] = request
        else:
            old = node.scroll_state[axis]
            node.scroll_state[axis] = request + [1 if old is None else old[2] + 1]
            node.runtime.wake()
        return self

    def properties(self):
        def policy(value):
            return 'auto' if value is None else 'scroll' if value else 'hidden'
        return {'vertical': policy(self.vertical), 'horizontal': policy(self.horizontal),
                'scroll_x': self.scroll_state[0], 'scroll_y': self.scroll_state[1]}


class Unsupported:
    pui_supported = False

    def __init__(self, *args, **kwargs):
        raise NotImplementedError('%s is not implemented by the Web backend' % type(self).__name__)


class Html(Unsupported):
    pass


class MarkDown(Unsupported):
    pass


class Image(WebNode):
    wire_type = 'Image'

    def __init__(self, path):
        super().__init__()
        self.path = path

    def properties(self):
        from pathlib import Path
        return {'src': self.runtime.images.register(self.path), 'alt': Path(self.path).name}


class Tree(Unsupported):
    pass


class Splitter(Unsupported):
    pass


class Dialog(Unsupported):
    pass


class Confirm(Unsupported):
    pass


class Prompt(Unsupported):
    pass


class MatplotlibCanvas(Unsupported):
    pass


Combobox = ComboBox
ComboboxItem = ComboBoxItem

from .canvas import Canvas
from .table import Table, TableNode
