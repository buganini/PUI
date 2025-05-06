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
