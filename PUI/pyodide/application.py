"""Application startup inside an initialized Pyodide module worker."""
from .. import _typing as _t
from .._browser.widgets import Application as BrowserApplication
from ..timeline import TimelineView as BaseTimelineView


class Application(BrowserApplication):
    def start(self, *, landlock=None, codex: _t.AIProvider = None, claude: _t.AIProvider = None, upload_limits=None):
        """Start rendering and return to the browser's existing event loop."""
        if any(value is not None and value is not False for value in (codex, claude)):
            import logging
            logging.getLogger('PUI').warning('pyodide does not support AI integration')
        from .._landlock import apply
        apply(landlock)
        if self.runtime is None:
            raise RuntimeError('Initialize the Pyodide runtime before constructing the application')
        from .._browser.uploads import UploadStore
        self.runtime.uploads = UploadStore(upload_limits=upload_limits)
        return self.runtime.start(self)


class TimelineView(BaseTimelineView):
    def _schedule(self):
        return self.root.runtime.loop.call_later(self.ttl_sec, self.timer_cb)
