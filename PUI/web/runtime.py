"""Native Web worker scheduling and HTTP resources for the browser runtime."""
import logging
import threading
from .._browser.runtime import Runtime as BrowserRuntime
from .images import ImageRegistry
from ..state_refs import StateRefs


class Runtime(BrowserRuntime):
    def __init__(self, loop, *, image_base='/pui/images'):
        super().__init__(loop, images=ImageRegistry(image_base),
                         lock=threading.Lock(), call_soon=loop.call_soon_threadsafe,
                         logger=logging.getLogger('PUI.web.widgets'))
        self.state_refs = StateRefs()

    def close(self):
        super().close()
        self.state_refs.clear()
