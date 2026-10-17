"""Private loopback JSON channel, separate from application stdout. No handshake."""
import atexit
import json
import os
import socket
import threading
from urllib.parse import quote
from ..state_refs import _json_value

MAX_MESSAGE = 1024 * 1024
_connection = None


def options_text(values):
    return '#'.join(quote(name, safe='') + '=' + quote(value, safe='')
                    for name, value in values.items())


def state_text(value):
    return value if isinstance(value, str) else json.dumps(value, default=_json_value,
        ensure_ascii=True, allow_nan=False, separators=(',', ':'))


def publish(name, value):
    if _connection is not None:
        _connection.publish(name, value)


class ChildConnection:
    def __init__(self, descriptor):
        endpoint = json.loads(descriptor)
        self.token = endpoint['token']
        self.socket = socket.create_connection(('127.0.0.1', endpoint['port']), timeout=5)
        self.socket.settimeout(None)
        self.lock = threading.Lock()
        self.closed = False
        self.post = self.quit = None
        self.stopping = False
        self.last = {}
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def ready(self, post, quit):
        with self.lock:
            self.post, self.quit = post, quit
            stopping = self.stopping
        if stopping:
            post(quit)

    def _read(self):
        try:
            with self.socket.makefile('rb') as stream:
                for line in iter(lambda: stream.readline(MAX_MESSAGE + 1), b''):
                    if len(line) > MAX_MESSAGE:
                        break
                    message = json.loads(line)
                    if message.get('token') != self.token:
                        break
                    if message.get('type') == 'stop':
                        break
        except (OSError, ValueError):
            pass
        finally:
            if not self.closed:
                self.stopping = True
                if self.post:
                    try:
                        self.post(self.quit)
                    except RuntimeError:
                        pass
                # Includes supervisor crash and a blocked/missing GUI event loop.
                timer = threading.Timer(5, lambda: os._exit(0))
                timer.daemon = True
                timer.start()

    def publish(self, name, value):
        try:
            text = state_text(value)
            with self.lock:
                if self.closed or self.last.get(name) == text:
                    return
                data = (json.dumps(dict(token=self.token, type='state', name=name, value=text)) + '\n').encode()
                if len(data) > MAX_MESSAGE:
                    raise ValueError('State ref exceeds IPC message limit')
                self.socket.sendall(data)
                self.last[name] = text
        except (TypeError, ValueError, OSError):
            import logging
            logging.getLogger('PUI').warning('Unable to publish State ref %r to supervisor', name)

    def close(self):
        self.closed = True
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.socket.close()


def connect():
    global _connection
    descriptor = os.environ.get('PUI_IPC')
    if descriptor and _connection is None:
        _connection = ChildConnection(descriptor)
        atexit.register(_connection.close)
    return _connection
