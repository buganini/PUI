from enum import Enum

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