from enum import Enum
from enum import IntEnum

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
