"""Importable worker application used by the real gateway tests."""
import os
from pathlib import Path
import signal
import tempfile
import time
from PUI.web import Application, Window, VBox, Label, Button, TextField, State


class App(Application):
    def setup(self):
        self.state = State()
        self.state.count = 0
        self.state.text = 1.23

    def increment(self, event):
        self.state.count += 1

    def content(self):
        with Window('Web test'):
            with VBox():
                Label('pid=' + str(os.getpid()))
                Label('count=' + str(self.state.count))
                Button('Increment').click(self.increment)
                TextField(self.state('text'))


class CrashApp(App):
    def increment(self, event):
        os._exit(9)


class AckTimeoutApp(App):
    def setup(self):
        from PUI.web import worker
        worker.RENDER_ACK_TIMEOUT = .1
        super().setup()


class EditApp(App):
    def content(self):
        with Window('Edit sequence test'):
            Label('count=' + str(self.state.count))
            TextField(self.state('text')).input(self.increment)


class BlockedApp(App):
    def increment(self, event):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        mark_blocked()
        time.sleep(3600)


class SlowStartup(App):
    def setup(self):
        mark_blocked()
        time.sleep(3600)


class BrokenStartup(App):
    def __init__(self):
        raise RuntimeError('Test startup failure')


def block_markers(pid):
    return list(Path(tempfile.gettempdir()).glob('pui-web-test-%s-*.marker' % pid))


def mark_blocked():
    # The fork supervisor intentionally retains its original environment.
    # Use a per-process test marker instead of changing environment after startup.
    with tempfile.NamedTemporaryFile(prefix='pui-web-test-%s-' % os.getpid(),
                                     suffix='.marker', delete=False) as marker:
        marker.write(b'entered')
