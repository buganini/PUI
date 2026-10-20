from enum import Enum
from enum import IntEnum

def window_title(node):
    """Keep explicit window titles; otherwise inherit a nonempty app title."""
    if node.title is not None:
        return node.title
    application = node
    while application.parent is not application:
        application = application.parent
    return getattr(application, 'title', '') or None

class Side(Enum):
    TOP = "n"
    RIGHT = "e"
    BOTTOM = "s"
    LEFT = "w"


class Anchor(Enum):
    LEFT_TOP = ("left" ,"top")
    LEFT_CENTER = ("left" ,"center")
    LEFT_BOTTOM = ("left" ,"bottom")
    CENTER_TOP = ("center" ,"top")
    CENTER = ("center" ,"center")
    CENTER_BOTTOM = ("center" ,"bottom")
    RIGHT_TOP = ("right" ,"top")
    RIGHT_CENTER = ("right" ,"center")
    RIGHT_BOTTOM = ("right" ,"bottom")

class MouseButton(IntEnum):
    NONE = 0
    LEFT = 1
    RIGHT = 2
    MIDDLE = 4
    X1 = 8
    X2 = 16

class KeyModifier(IntEnum):
    SHIFT = 1
    CTRL = 2
    ALT = 4
    META = 8

def checkbox_get(model, value):
    from .state import StateList, StateDict
    if isinstance(model.value, list) or isinstance(model.value, StateList):
        return value in model.value
    elif isinstance(model.value, dict) or isinstance(model.value, StateDict):
        return model.value.get(value, False)
    else:
        return bool(model.value)


def checkbox_set(model, checked, value):
    from .state import StateList, StateDict
    if isinstance(model.value, list) or isinstance(model.value, StateList):
        if checked:
            if not value in model.value:
                model.value.append(value)
        else:
            try:
                model.value.remove(value)
            except:
                pass
    elif isinstance(model.value, dict) or isinstance(model.value, StateDict):
        if checked:
            model.value[value] = True
        else:
            model.value.pop(value, None)
    else:
        model.value = checked


def combobox_get(items, index_model=None, text_model=None, editable=False, state=None):
    """Resolve selected labels and free text without losing an editable buffer."""
    state = state or {'key': None, 'text': ''}
    if index_model is not None:
        index = index_model.value
        if isinstance(index, int) and 0 <= index < len(items):
            return index, items[index].text
        return -1, (str(text_model.value) if text_model is not None else state['text']) if editable else ''
    if text_model is not None:
        text = str(text_model.value)
        if editable and state.get('editing') and text == state['text']:
            return -1, text
        index = next((i for i, item in enumerate(items) if str(item.value) == text), -1)
        return index, items[index].text if index >= 0 else text
    index = next((i for i, item in enumerate(items) if item.key == state['key']), -1)
    return index, items[index].text if index >= 0 else state['text'] if editable else ''


def combobox_set_text(index_model, text_model, text, state=None):
    if state is not None:
        state.update(key=None, text=text, editing=True)
    if index_model is not None:
        index_model.value = -1
    if text_model is not None:
        text_model.value = text


def combobox_record_selection(items, index, state):
    if 0 <= index < len(items):
        state.update(key=items[index].key, text=items[index].text, editing=False)
    else:
        state.update(key=None, text='')
