"""Application startup inside an initialized Pyodide module worker."""
from .._browser.widgets import Application as BrowserApplication
from ..timeline import TimelineView as BaseTimelineView


class Application(BrowserApplication):
    def start(self):
        """Start rendering and return to the browser's existing event loop."""
        if self.runtime is None:
            raise RuntimeError('Initialize the Pyodide runtime before constructing the application')
        return self.runtime.start(self)


class TimelineView(BaseTimelineView):
    def _schedule(self):
        return self.root.runtime.loop.call_later(self.ttl_sec, self.timer_cb)
