"""Ordered local messages and render credit on Pyodide's existing asyncio loop."""
import asyncio
from collections import deque
import traceback

from .._browser.runtime import Runtime as BrowserRuntime
from .._browser.render import RenderStream
from .._browser.schema import ProtocolError, SAFE_INTEGER, validate_data
from .._browser.messages import validate_client_body
from .images import ImageRegistry

BRIDGE_VERSION = 1


class Runtime(BrowserRuntime):
    def _publish_state_ref(self, name, value):
        from . import state_ref_publish
        state_ref_publish(name, value)

    def __init__(self, loop, send, *, epoch, build):
        super().__init__(loop, images=ImageRegistry())
        self.send = send
        self.epoch, self.build = epoch, build
        self.received = self.outgoing = self.processed = 0
        self.incoming = deque()
        self.stream = RenderStream()
        self.registered_images = set()
        self.task = None
        self.redraw_pending = False

    def wake(self):
        self.redraw_pending = True
        super().wake()

    def emit(self, kind, body):
        self.outgoing += 1
        self.send({'v': BRIDGE_VERSION, 'epoch': self.epoch, 'seq': self.outgoing,
                   'type': kind, 'body': body})

    def start(self, app):
        if self.task is not None or self.closed:
            raise RuntimeError('This Pyodide runtime has already started')
        if app.runtime is not self:
            raise RuntimeError('Application belongs to another runtime')
        self.app = app
        app.sync()
        self.task = self.loop.create_task(self._run())
        return self.task

    def receive(self, message):
        if self.closed:
            return
        validate_data(message)
        if (type(message) is not dict or set(message) != {'v', 'epoch', 'seq', 'type', 'body'} or
                type(message['v']) is not int or message['v'] != BRIDGE_VERSION or
                message['epoch'] != self.epoch or type(message['seq']) is not int or
                not 0 < message['seq'] <= SAFE_INTEGER or message['seq'] != self.received + 1):
            raise ProtocolError('BAD_SEQUENCE', 'Invalid worker epoch or sequence')
        validate_client_body(message['type'], message['body'])
        if len(self.incoming) >= 256:
            raise ProtocolError('LIMIT_EXCEEDED', 'Worker input queue is full')
        self.received = message['seq']
        self.incoming.append(message)
        self.changed.set()

    def _resources(self):
        entries = self.images.retain(self.stream.retained_states())
        keep = {entry['ref'] for entry in entries}
        if keep != self.registered_images:
            self.emit('resources', {'add': [entry for entry in entries
                                          if entry['ref'] not in self.registered_images],
                                    'keep': sorted(keep)})
            self.registered_images = keep

    async def _run(self):
        try:
            self.emit('ready', {'build': self.build, 'max_pending_actions': 64, 'upload_limits': self.uploads.limits if self.uploads else {}})
            refresh = True
            while not self.quit_requested:
                if self.changed.is_set():
                    self.changed.clear()
                if self.redraw_pending:
                    self.redraw_pending = False
                    refresh = True
                if self.incoming:
                    message = self.incoming.popleft()
                    self.processed = message['seq']
                    kind, body = message['type'], message['body']
                    if kind in ('event', 'binding_write'):
                        try:
                            status, code = self.action(kind, body, render_rev=self.stream.issued_rev)
                        except Exception:
                            traceback.print_exc()
                            status, code = 'error', 'APP_ERROR'
                        self.emit('result', {'reply_to': self.processed, 'status': status, 'code': code})
                        refresh = True
                    elif kind == 'ack':
                        self.stream.acknowledge(**body)
                    elif kind == 'resync':
                        self.stream.resync(**body)
                        refresh = True
                    elif kind in ('measure', 'canvas_ack'):
                        refresh = self.canvas_control(kind, body) or refresh
                    elif kind == 'close':
                        self.quit_requested = True
                if self.quit_requested:
                    break
                if refresh:
                    self.flush()
                    self.redraw_pending = False
                    self.stream.offer(self.snapshot(copy=False), processed_seq=self.processed, copy=False, trusted=True)
                    refresh = False
                for result in self.drop_results:
                    self.emit('drop_result', result)
                self.drop_results.clear()
                self._resources()
                render = self.stream.next_render(copy=False)
                if render is not None:
                    self.emit('render', render)
                if self.incoming:
                    await asyncio.sleep(0)
                else:
                    await self.changed.wait()
            self.emit('close', {'reason': 'Application quit'})
        except Exception as error:
            traceback.print_exc()
            self.emit('error', {'code': getattr(error, 'code', 'APP_ERROR'), 'reply_to': None,
                                'fatal': True, 'message': str(error)})
        finally:
            self.close()

    def upload_begin(self, node_id, token, names):
        target = self.drop_targets().get(node_id)
        if self.closed or target is None or target['token'] != token:
            raise ValueError('Drop target is no longer available')
        key = self.uploads.begin()
        try:
            return {'key': key, 'files': [self.uploads.add(key, name, target['extensions']) for name in names]}
        except Exception:
            self.uploads.discard(key)
            raise

    def close(self):
        self.incoming.clear()
        super().close()
