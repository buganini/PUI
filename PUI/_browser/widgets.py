"""Shared browser widgets backed by retained, serializable element records."""
from __future__ import annotations
from ..grid import GridMixin
from ..adaptive import BoxMixin as _BoxMixin, HVBoxMixin as _HVBoxMixin, VHBoxMixin as _VHBoxMixin
from .. import _typing as _t
from ..common import Side
from ..refs import NodeBinder as _NodeBinder
from dataclasses import dataclass, field
import math
from ..node import PUINode
from ..view import PUIView as BaseView
from ..views import ViewsMixin
from ..selection import TabsMixin
from ..common import checkbox_get, checkbox_set, combobox_get, combobox_record_selection, combobox_set_text
from ..state import Unstate
from ..node import PUIEvent
from .schema import SAFE_INTEGER

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
    def _publish_state_ref(self, name, value):
        if self.runtime is not None:
            self.runtime._publish_state_ref(name, value)

    def __init__(self, *args):
        self.runtime = _current_runtime
        super().__init__(*args)

    def update(self, prev=None):
        refs = getattr(self.runtime, 'state_refs', None)
        if refs is None:
            super().update(prev)
        else:
            with refs.collect(self):
                super().update(prev)

    def redraw(self):
        if self.retired_by or self.destroyed:
            return
        self.dirty = True
        if self.runtime is not None:
            self.runtime.queue_view(self)
        else:
            super().redraw()


class Application(PUIView):
    def __init__(self, *args: _t.Any, title: str = '') -> None:
        super().__init__(*args)
        self.title = title

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

    def run(self, *, codex: _t.AIProvider = None, claude: _t.AIProvider = None, **kwargs):
        # The gateway must not build a UI; each client worker creates its own app.
        if codex is not None:
            kwargs['codex'] = codex
        if claude is not None:
            kwargs['claude'] = claude
        return self.start(**kwargs)



class BrowserNode(PUINode):
    def _observe_size(self):
        # A subscription made after mount must also reach the browser.
        if self.ui.id in self.runtime.nodes:
            self.runtime.wake()
        return None

    def get_poster(self) -> _t.Poster:
        from ..poster import make_poster
        loop = self.root.runtime.loop
        return make_poster(loop.call_soon_threadsafe, loop.call_later)

    pui_terminal = True
    wire_type = None
    model_roles = ()
    native_event = None

    def native_context(self):
        return None

    def __init__(self):
        self.runtime = _current_runtime
        if self.runtime is None:
            raise RuntimeError('Browser widgets must be built inside an application runtime')
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
            'mouseenter': '_onMouseEnter', 'mouseleave': '_onMouseLeave', 'wheel': '_onWheel'}
        if not isinstance(self, TextField):
            callbacks.update(input='_onInput', change='_onChanged')
        if isinstance(self, ComboBox):
            callbacks.pop('change')
            if self.editable:
                callbacks.pop('input')
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
        if weight is not None:
            number(weight, 'fontWeight', 1)
            if weight > 1000:
                raise ValueError('Web numeric fontWeight must be between 1 and 1000')
        if self.style_fontfamily is not None and not isinstance(self.style_fontfamily, str):
            raise ValueError('Web fontFamily must be a string')


class VBox(_BoxMixin, BrowserNode):
    _native_box_inverse = True
    pui_terminal = False
    wire_type = 'VBox'

    def properties(self):
        return {'inverse': self._inverse} if self.wire_type in ('VBox', 'HBox') else {}


class HBox(VBox):
    wire_type = 'HBox'


class Grid(GridMixin, VBox):
    wire_type = 'Grid'
    pui_grid_layout = True

    def postSync(self):
        self.grid_cells([element.node for element in self.ui.children])
        super().postSync()

    def properties(self):
        return {'columns': self._grid_columns}


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

    def __init__(self, tabposition: Side = Side.Top, model: _t.Binding[_t.Any] | None = None) -> None:
        super().__init__(model=model)
        if not isinstance(tabposition, Side):
            raise TypeError('tabposition must be a Side')
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
        return {'selected': self.selected, 'position': self.tabposition.value}

    def handle_native(self, data):
        index = next((i for i, page in enumerate(self.children) if page.ui.id == data['page_id']), None)
        if index is None:
            return False
        self._native_selected(index)
        return True


class Tab(VBox):
    wire_type = 'Tab'

    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = str(label)
        self.layout(padding=0)

    def properties(self):
        return {'label': self.label}

    def validate_options(self):
        super().validate_options()
        if not isinstance(self.non_virtual_parent, Tabs):
            raise ValueError('Tab requires a Tabs parent')


class _WindowBinder(_NodeBinder):
    def _warn(self, enabled, command):
        self._node(enabled)
        import logging
        logging.getLogger('PUI').warning('Browser does not support Window.%s', command)

    def maximize(self, enabled: bool):
        self._warn(enabled, 'maximize')

    def minimize(self, enabled: bool):
        self._warn(enabled, 'minimize')

    def fullscreen(self, enabled: bool):
        self._warn(enabled, 'fullscreen')


class Window(VBox):
    def __pui_binder__(self):
        return _WindowBinder(self)

    wire_type = 'Window'

    def __init__(
        self,
        title: str | None = None,
        icon: _t.Any = None,
        size: tuple[int, int] | None = None,
        maximize: bool | None = False,
        fullscreen: bool | None = False,
    ) -> None:
        super().__init__()
        if icon is not None:
            self.runtime.logger.warning('Web Window ignores icon; window icons are not implemented')
        if fullscreen:
            self.runtime.logger.warning('Web Window ignores fullscreen; fullscreen is not implemented')
        self.title = None if title is None else str(title)
        # Browser layout owns the available space, including embedded mounts.
        # Desktop initial size and maximize do not constrain the root element.

    def properties(self):
        title = self.title if self.title is not None else self.runtime.app.title or 'PUI'
        return {'title': title}


class Label(BrowserNode):
    wire_type = 'Label'

    def __init__(self, text: _t.Any, selectable: bool = False) -> None:
        super().__init__()
        self.text, self.selectable = str(text), bool(selectable)

    def properties(self):
        return {'text': self.text, 'selectable': self.selectable}


class Button(BrowserNode):
    wire_type = 'Button'

    def __init__(self, text: _t.Any, *, disabled: bool = False) -> None:
        super().__init__()
        self.text, self.disabled = str(text), bool(disabled)

    def properties(self):
        return {'text': self.text, 'disabled': self.disabled}


class TextField(BrowserNode):
    wire_type = 'TextField'
    model_roles = ('model', 'edit_model')

    def __init__(
        self,
        model: _t.Binding[_t.Any],
        edit_model: _t.Binding[_t.Any] | None = None,
        *,
        placeholder: str | None = None,
    ) -> None:
        super().__init__()
        self.model, self.edit_model = model, edit_model
        self.placeholder = '' if placeholder is None else str(placeholder)

    def properties(self):
        return {'text': str(self.model.value), 'placeholder': self.placeholder}


class TextEdit(TextField):
    """Multiline editor sharing TextField's retained binding protocol."""
    wire_type = 'TextEdit'

    def __init__(
        self,
        model: _t.Binding[_t.Any],
        edit_model: _t.Binding[_t.Any] | None = None,
        *,
        placeholder: str | None = None,
        readonly: bool = False,
        wrap: bool = True,
    ) -> None:
        super().__init__(model, edit_model, placeholder=placeholder)
        self.readonly = bool(readonly)
        self.wrap = bool(wrap)

    def properties(self):
        return dict(super().properties(), readonly=self.readonly, wrap=self.wrap)


class MaskedField(TextField):
    """TextField rendered as a native password input."""
    wire_type = 'MaskedField'


class Checkbox(BrowserNode):
    wire_type = 'Checkbox'
    model_roles = ('model',)
    native_event = 'toggle'

    def __init__(
        self,
        text: _t.Any,
        model: _t.Binding[_t.Any],
        value: _t.Any = None,
        *,
        disabled: bool = False,
    ) -> None:
        super().__init__()
        self.text, self.model = str(text), model
        self.value = text if value is None else value
        self.disabled = bool(disabled)

    def properties(self):
        return {'text': self.text, 'checked': bool(checkbox_get(self.model, self.value)),
                'disabled': self.disabled}

    def native_context(self):
        return Unstate(self.value)

    def handle_native(self, data):
        checkbox_set(self.model, data['checked'], self.value)
        event = PUIEvent()
        event.value = data['checked']
        self._clicked(event)
        return True


class RadioButton(BrowserNode):
    wire_type = 'RadioButton'
    model_roles = ('model',)
    native_event = 'activate'

    def __init__(self, text: _t.Any, value: _t.Any, model: _t.Binding[_t.Any], *, disabled: bool = False) -> None:
        super().__init__()
        self.text, self.value, self.model = str(text), value, model
        self.disabled = bool(disabled)

    def properties(self):
        return {'text': self.text, 'checked': self.model.value == self.value,
                'disabled': self.disabled}

    def native_context(self):
        return Unstate(self.value)

    def handle_native(self, data):
        self.model.value = self.value
        event = PUIEvent()
        event.value = self.value
        self._clicked(event)
        return True


class ComboBox(BrowserNode):
    wire_type = 'ComboBox'
    pui_terminal = False
    model_roles = ('index_model', 'text_model', 'edit_model')
    native_event = 'choose'

    def __init__(
        self,
        editable: bool = False,
        *,
        index_model: _t.Binding[_t.Any] | None = None,
        text_model: _t.Binding[_t.Any] | None = None,
        edit_model: _t.Binding[_t.Any] | None = None,
        disabled: bool = False,
        autoexpand: bool = True,
    ) -> None:
        super().__init__()
        self.editable = bool(editable)
        self.native_event = 'edit' if self.editable else 'choose'
        self.index_model, self.text_model = index_model, text_model
        self.autoexpand = bool(autoexpand)
        self.disabled = bool(disabled)
        self.edit_model = edit_model
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
        return {'disabled': self.disabled, 'selected': self.children[index].ui.id if index >= 0 else None,
                'editable': self.editable, 'autoexpand': self.autoexpand, 'text': text}

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


class ComboBoxItem(BrowserNode):
    wire_type = 'ComboBoxItem'

    def __init__(self, text: _t.Any, value: _t.Any = None) -> None:
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


class Text(BrowserNode):
    wire_type = 'Text'

    def __init__(self, text: _t.Any) -> None:
        super().__init__()
        self.text = str(text)

    def properties(self):
        return {'text': self.text}


class Spacer(BrowserNode):
    wire_type = 'Spacer'

    def __init__(self):
        super().__init__()
        self.layout(weight=1)


class Divider(BrowserNode):
    wire_type = 'Divider'


class ProgressBar(BrowserNode):
    wire_type = 'ProgressBar'

    def __init__(self, progress: _t.Number, maximum: _t.Number = 1) -> None:
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

    def __init__(self, vertical: bool | None = None, horizontal: bool | None = False) -> None:
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


class Html(Label):
    """Trusted HTML fragment rendered inside an isolated browser shadow root."""
    wire_type = 'Html'


class MarkDown(Unsupported):
    pass


class Image(BrowserNode):
    wire_type = 'Image'

    def __init__(self, path: _t.Any) -> None:
        super().__init__()
        self.path = path

    def properties(self):
        from pathlib import Path
        return {'src': self.runtime.images.register(self.path), 'alt': Path(self.path).name}


class Tree(Unsupported):
    pass


class Splitter(VBox):
    wire_type = 'Splitter'

    def __init__(self, vertical: bool = False) -> None:
        super().__init__()
        self.vertical = bool(vertical)

    def properties(self):
        return {'vertical': self.vertical}


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


class _AdaptiveLayout(VBox):
    def properties(self):
        return dict(super().properties(), direction='row' if self.container_x else 'column')


class HVBox(_HVBoxMixin, _AdaptiveLayout):
    pass


class VHBox(_VHBoxMixin, _AdaptiveLayout):
    pass
