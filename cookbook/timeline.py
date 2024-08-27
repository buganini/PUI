from .config import *

@PUI
def TimelineViewExample():
    from datetime import datetime

    with TimelineView(ttl_sec=1):
        Label(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    Spacer()